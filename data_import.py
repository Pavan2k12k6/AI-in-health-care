import csv
import json
import logging
from datetime import datetime
from flask import flash
from app import db
from models import Patient, MedicalCondition, GenotypeData
from sqlalchemy.exc import SQLAlchemyError

def parse_date(date_str):
    """Parse a date string into a Python date object"""
    try:
        # Try different date formats
        for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d', '%d-%m-%Y']:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        raise ValueError(f"Could not parse date: {date_str}")
    except Exception as e:
        logging.error(f"Error parsing date {date_str}: {str(e)}")
        return None

def validate_patient_data(row, required_fields):
    """Validate that the patient data has all required fields"""
    missing_fields = [field for field in required_fields if field not in row or not row[field]]
    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"
    return True, None

def import_patients_from_csv(file_path, provider_id):
    """
    Import patients from a CSV file
    
    Args:
        file_path (str): Path to the CSV file
        provider_id (int): ID of the healthcare provider importing the data
        
    Returns:
        tuple: (success_count, error_count, errors)
    """
    success_count = 0
    error_count = 0
    errors = []
    
    required_fields = ['patient_id', 'first_name', 'last_name', 'date_of_birth', 'gender']
    
    try:
        with open(file_path, 'r', encoding='utf-8') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            
            for row in csv_reader:
                try:
                    # Validate required fields
                    is_valid, error_msg = validate_patient_data(row, required_fields)
                    if not is_valid:
                        error_count += 1
                        errors.append(f"Row {csv_reader.line_num}: {error_msg}")
                        continue
                    
                    # Check if patient already exists
                    existing_patient = Patient.query.filter_by(patient_id=row['patient_id']).first()
                    if existing_patient:
                        # Update existing patient
                        update_patient_data(existing_patient, row, provider_id)
                        db.session.commit()
                        success_count += 1
                    else:
                        # Create new patient
                        new_patient = create_patient_from_row(row, provider_id)
                        db.session.add(new_patient)
                        db.session.commit()
                        
                        # Process medical conditions if present
                        if 'medical_conditions' in row and row['medical_conditions']:
                            add_medical_conditions(new_patient.id, row['medical_conditions'])
                        
                        # Process genotype data if present
                        if 'genotype_data' in row and row['genotype_data']:
                            add_genotype_data(new_patient.id, row['genotype_data'])
                        
                        success_count += 1
                
                except Exception as e:
                    db.session.rollback()
                    error_count += 1
                    errors.append(f"Row {csv_reader.line_num}: {str(e)}")
                    logging.error(f"Error importing patient data: {str(e)}")
    
    except Exception as e:
        error_count += 1
        errors.append(f"File error: {str(e)}")
        logging.error(f"Error opening or reading CSV file: {str(e)}")
    
    return success_count, error_count, errors

def create_patient_from_row(row, provider_id):
    """Create a new Patient object from a CSV row"""
    dob = parse_date(row['date_of_birth'])
    if not dob:
        raise ValueError("Invalid date of birth format")
    
    weight = None
    if 'weight' in row and row['weight']:
        try:
            weight = float(row['weight'])
        except ValueError:
            logging.warning(f"Invalid weight value: {row['weight']}")
    
    new_patient = Patient(
        patient_id=row['patient_id'],
        first_name=row['first_name'],
        last_name=row['last_name'],
        date_of_birth=dob,
        gender=row['gender'],
        weight=weight,
        provider_id=provider_id
    )
    
    return new_patient

def update_patient_data(patient, row, provider_id):
    """Update an existing Patient with data from CSV row"""
    # Only update if the provider is the same
    if patient.provider_id != provider_id:
        raise ValueError("You don't have permission to update this patient")
    
    # Update basic fields
    patient.first_name = row['first_name']
    patient.last_name = row['last_name']
    
    dob = parse_date(row['date_of_birth'])
    if dob:
        patient.date_of_birth = dob
    
    patient.gender = row['gender']
    
    if 'weight' in row and row['weight']:
        try:
            patient.weight = float(row['weight'])
        except ValueError:
            logging.warning(f"Invalid weight value: {row['weight']}")

def add_medical_conditions(patient_id, conditions_str):
    """Add medical conditions to a patient"""
    try:
        # Try to parse as JSON
        try:
            conditions = json.loads(conditions_str)
        except json.JSONDecodeError:
            # Fall back to comma-separated string
            conditions = [cond.strip() for cond in conditions_str.split(',')]
        
        # If conditions is a list of strings
        if isinstance(conditions, list):
            for condition_name in conditions:
                condition = MedicalCondition(
                    name=condition_name,
                    patient_id=patient_id
                )
                db.session.add(condition)
        
        # If conditions is a list of dicts
        elif isinstance(conditions, list) and all(isinstance(c, dict) for c in conditions):
            for condition_dict in conditions:
                diagnosis_date = None
                if 'diagnosis_date' in condition_dict and condition_dict['diagnosis_date']:
                    diagnosis_date = parse_date(condition_dict['diagnosis_date'])
                
                condition = MedicalCondition(
                    name=condition_dict['name'],
                    diagnosis_date=diagnosis_date,
                    notes=condition_dict.get('notes', ''),
                    patient_id=patient_id
                )
                db.session.add(condition)
        
        db.session.commit()
    
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error adding medical conditions: {str(e)}")
        raise

def add_genotype_data(patient_id, genotype_str):
    """Add genotype data to a patient"""
    try:
        # Try to parse as JSON
        try:
            genotype_data = json.loads(genotype_str)
        except json.JSONDecodeError:
            # Fall back to basic format: gene:variant,gene:variant
            genotype_data = []
            for item in genotype_str.split(','):
                if ':' in item:
                    gene, variant = item.strip().split(':', 1)
                    genotype_data.append({'gene': gene, 'variant': variant})
        
        # Process the genotype data
        if isinstance(genotype_data, dict):
            # Handle case where genotype_data is a dict with gene keys
            for gene, variant in genotype_data.items():
                genotype = GenotypeData(
                    gene=gene,
                    variant=str(variant),
                    patient_id=patient_id
                )
                db.session.add(genotype)
        
        elif isinstance(genotype_data, list):
            # Handle case where genotype_data is a list of dicts
            for genotype_dict in genotype_data:
                if isinstance(genotype_dict, dict) and 'gene' in genotype_dict and 'variant' in genotype_dict:
                    genotype = GenotypeData(
                        gene=genotype_dict['gene'],
                        variant=genotype_dict['variant'],
                        phenotype=genotype_dict.get('phenotype', ''),
                        significance=genotype_dict.get('significance', ''),
                        patient_id=patient_id
                    )
                    db.session.add(genotype)
        
        db.session.commit()
    
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error adding genotype data: {str(e)}")
        raise

def get_genotype_data_for_patient(patient_id):
    """
    Get genotype data for a patient in a format suitable for analysis
    
    Returns:
        dict: Dictionary mapping gene names to variant values
    """
    try:
        genotype_records = GenotypeData.query.filter_by(patient_id=patient_id).all()
        genotype_dict = {record.gene: record.variant for record in genotype_records}
        return genotype_dict
    except SQLAlchemyError as e:
        logging.error(f"Database error retrieving genotype data: {str(e)}")
        return {}
    except Exception as e:
        logging.error(f"Error retrieving genotype data: {str(e)}")
        return {}