from flask import render_template, url_for, flash, redirect, request, jsonify, session
from flask_login import login_user, current_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, date
import os
import json
from app import app, db
from models import User, Patient, Medication, MedicalCondition, Allergy, Prescription, DrugInteraction, GenotypeData, GenotypeAnalysis
from drug_interaction_api import check_interactions, get_rxcui_for_name
from genotype_analysis import analyze_drug_metabolism
from data_import import import_patients_from_csv, get_genotype_data_for_patient
from utils import format_date
import logging

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user, remember=True)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Login unsuccessful. Please check your username and password.', 'danger')
    
    return render_template('login.html', title='Login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return render_template('register.html', title='Register')
        
        user_exists = User.query.filter((User.username == username) | (User.email == email)).first()
        if user_exists:
            flash('Username or email already exists. Please try a different one.', 'danger')
            return render_template('register.html', title='Register')
        
        new_user = User(username=username, email=email, first_name=first_name, last_name=last_name)
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Your account has been created! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', title='Register')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    patients = Patient.query.filter_by(provider_id=current_user.id).all()
    
    # Get the number of pending prescriptions for each patient
    for patient in patients:
        patient.pending_count = Prescription.query.filter_by(
            patient_id=patient.id, 
            status='pending'
        ).count()
    
    return render_template('dashboard.html', title='Dashboard', patients=patients)

@app.route('/patient/add', methods=['GET', 'POST'])
@login_required
def add_patient():
    if request.method == 'POST':
        try:
            patient_id = request.form.get('patient_id')
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            dob_str = request.form.get('date_of_birth')
            gender = request.form.get('gender')
            weight = request.form.get('weight')
            
            # Convert string date to Python date object
            dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
            
            # Check if patient with this ID already exists
            existing_patient = Patient.query.filter_by(patient_id=patient_id).first()
            if existing_patient:
                flash('A patient with this ID already exists.', 'danger')
                return render_template('add_patient.html', title='Add Patient')
            
            new_patient = Patient(
                patient_id=patient_id,
                first_name=first_name,
                last_name=last_name,
                date_of_birth=dob,
                gender=gender,
                weight=float(weight) if weight else None,
                provider_id=current_user.id
            )
            
            db.session.add(new_patient)
            db.session.commit()
            
            flash('Patient added successfully!', 'success')
            return redirect(url_for('patient_profile', patient_id=new_patient.id))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding patient: {str(e)}', 'danger')
            logging.error(f"Error adding patient: {e}")
    
    return render_template('add_patient.html', title='Add Patient')

@app.route('/patient/<int:patient_id>')
@login_required
def patient_profile(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    
    # Ensure the current user is the provider for this patient
    if patient.provider_id != current_user.id:
        flash('You do not have permission to view this patient profile.', 'danger')
        return redirect(url_for('dashboard'))
    
    medications = Medication.query.filter_by(patient_id=patient.id, active=True).all()
    medical_conditions = MedicalCondition.query.filter_by(patient_id=patient.id).all()
    allergies = Allergy.query.filter_by(patient_id=patient.id).all()
    prescriptions = Prescription.query.filter_by(patient_id=patient.id).order_by(Prescription.created_at.desc()).all()
    
    return render_template(
        'patient_profile.html',
        title=f'Patient: {patient.first_name} {patient.last_name}',
        patient=patient,
        medications=medications,
        medical_conditions=medical_conditions,
        allergies=allergies,
        prescriptions=prescriptions,
        format_date=format_date
    )

@app.route('/patient/<int:patient_id>/add_medication', methods=['POST'])
@login_required
def add_medication(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    
    # Ensure the current user is the provider for this patient
    if patient.provider_id != current_user.id:
        flash('You do not have permission to add medications for this patient.', 'danger')
        return redirect(url_for('dashboard'))
    
    medication_name = request.form.get('medication_name')
    dosage = request.form.get('dosage')
    frequency = request.form.get('frequency')
    start_date_str = request.form.get('start_date')
    
    # Get RxCUI for the medication
    rxcui = get_rxcui_for_name(medication_name)
    
    # Convert string date to Python date object if provided
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else date.today()
    
    new_medication = Medication(
        name=medication_name,
        rxcui=rxcui,
        dosage=dosage,
        frequency=frequency,
        start_date=start_date,
        patient_id=patient.id,
        active=True
    )
    
    db.session.add(new_medication)
    db.session.commit()
    
    flash('Medication added successfully!', 'success')
    return redirect(url_for('patient_profile', patient_id=patient.id))

@app.route('/patient/<int:patient_id>/add_condition', methods=['POST'])
@login_required
def add_condition(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    
    # Ensure the current user is the provider for this patient
    if patient.provider_id != current_user.id:
        flash('You do not have permission to add conditions for this patient.', 'danger')
        return redirect(url_for('dashboard'))
    
    condition_name = request.form.get('condition_name')
    diagnosis_date_str = request.form.get('diagnosis_date')
    notes = request.form.get('notes')
    
    # Convert string date to Python date object if provided
    diagnosis_date = datetime.strptime(diagnosis_date_str, '%Y-%m-%d').date() if diagnosis_date_str else None
    
    new_condition = MedicalCondition(
        name=condition_name,
        diagnosis_date=diagnosis_date,
        notes=notes,
        patient_id=patient.id
    )
    
    db.session.add(new_condition)
    db.session.commit()
    
    flash('Medical condition added successfully!', 'success')
    return redirect(url_for('patient_profile', patient_id=patient.id))

@app.route('/patient/<int:patient_id>/add_allergy', methods=['POST'])
@login_required
def add_allergy(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    
    # Ensure the current user is the provider for this patient
    if patient.provider_id != current_user.id:
        flash('You do not have permission to add allergies for this patient.', 'danger')
        return redirect(url_for('dashboard'))
    
    allergen = request.form.get('allergen')
    reaction = request.form.get('reaction')
    severity = request.form.get('severity')
    
    new_allergy = Allergy(
        allergen=allergen,
        reaction=reaction,
        severity=severity,
        patient_id=patient.id
    )
    
    db.session.add(new_allergy)
    db.session.commit()
    
    flash('Allergy added successfully!', 'success')
    return redirect(url_for('patient_profile', patient_id=patient.id))

@app.route('/patient/<int:patient_id>/prescribe', methods=['GET', 'POST'])
@login_required
def add_prescription(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    
    # Ensure the current user is the provider for this patient
    if patient.provider_id != current_user.id:
        flash('You do not have permission to prescribe for this patient.', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        medication_name = request.form.get('medication_name')
        dosage = request.form.get('dosage')
        frequency = request.form.get('frequency')
        indication = request.form.get('indication')
        
        # Get RxCUI for the medication
        rxcui = get_rxcui_for_name(medication_name)
        
        new_prescription = Prescription(
            medication_name=medication_name,
            rxcui=rxcui,
            dosage=dosage,
            frequency=frequency,
            indication=indication,
            status='pending',
            patient_id=patient.id,
            provider_id=current_user.id
        )
        
        db.session.add(new_prescription)
        db.session.commit()
        
        # Check for drug interactions
        current_medications = Medication.query.filter_by(patient_id=patient.id, active=True).all()
        
        for med in current_medications:
            if med.rxcui and rxcui:
                # Check for interactions between the new prescription and existing medications
                interactions = check_interactions(rxcui, med.rxcui)
                
                if interactions:
                    for interaction in interactions:
                        new_interaction = DrugInteraction(
                            drug1_name=medication_name,
                            drug1_rxcui=rxcui,
                            drug2_name=med.name,
                            drug2_rxcui=med.rxcui,
                            description=interaction.get('description', ''),
                            severity=interaction.get('severity', 'unknown'),
                            source=interaction.get('source', ''),
                            recommendation=interaction.get('recommendation', ''),
                            prescription_id=new_prescription.id
                        )
                        
                        db.session.add(new_interaction)
            
        db.session.commit()
        
        return redirect(url_for('interaction_results', prescription_id=new_prescription.id))
    
    return render_template('add_prescription.html', title='Add Prescription', patient=patient)

@app.route('/prescription/<int:prescription_id>/results')
@login_required
def interaction_results(prescription_id):
    prescription = Prescription.query.get_or_404(prescription_id)
    patient = Patient.query.get_or_404(prescription.patient_id)
    
    # Ensure the current user is the provider for this patient
    if patient.provider_id != current_user.id:
        flash('You do not have permission to view this prescription.', 'danger')
        return redirect(url_for('dashboard'))
    
    interactions = DrugInteraction.query.filter_by(prescription_id=prescription.id).all()
    
    # Count interactions by severity
    severity_counts = {
        'mild': 0,
        'moderate': 0,
        'severe': 0,
        'unknown': 0
    }
    
    for interaction in interactions:
        severity = interaction.severity.lower() if interaction.severity else 'unknown'
        if severity in severity_counts:
            severity_counts[severity] += 1
        else:
            severity_counts['unknown'] += 1
    
    return render_template(
        'interaction_results.html',
        title='Drug Interaction Results',
        prescription=prescription,
        patient=patient,
        interactions=interactions,
        severity_counts=severity_counts
    )

@app.route('/prescription/<int:prescription_id>/update', methods=['POST'])
@login_required
def update_prescription_status(prescription_id):
    prescription = Prescription.query.get_or_404(prescription_id)
    patient = Patient.query.get_or_404(prescription.patient_id)
    
    # Ensure the current user is the provider for this patient
    if patient.provider_id != current_user.id:
        flash('You do not have permission to update this prescription.', 'danger')
        return redirect(url_for('dashboard'))
    
    new_status = request.form.get('status')
    
    if new_status in ['approved', 'rejected']:
        prescription.status = new_status
        
        if new_status == 'approved':
            # Add to active medications if approved
            new_medication = Medication(
                name=prescription.medication_name,
                rxcui=prescription.rxcui,
                dosage=prescription.dosage,
                frequency=prescription.frequency,
                start_date=date.today(),
                patient_id=patient.id,
                active=True
            )
            db.session.add(new_medication)
        
        db.session.commit()
        flash(f'Prescription has been {new_status}.', 'success')
    else:
        flash('Invalid status provided.', 'danger')
    
    return redirect(url_for('patient_profile', patient_id=patient.id))

@app.route('/medication/<int:medication_id>/toggle', methods=['POST'])
@login_required
def toggle_medication(medication_id):
    medication = Medication.query.get_or_404(medication_id)
    patient = Patient.query.get_or_404(medication.patient_id)
    
    # Ensure the current user is the provider for this patient
    if patient.provider_id != current_user.id:
        flash('You do not have permission to update this medication.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Toggle the active status
    medication.active = not medication.active
    
    if not medication.active:
        medication.end_date = date.today()
    else:
        medication.end_date = None
    
    db.session.commit()
    
    status = "activated" if medication.active else "deactivated"
    flash(f'Medication {status} successfully!', 'success')
    
    return redirect(url_for('patient_profile', patient_id=patient.id))

@app.route('/import/patients', methods=['GET', 'POST'])
@login_required
def import_patients():
    """Route for importing patients from CSV file"""
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        
        # If user does not select file, browser also submits an empty part without filename
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Import patients from the CSV file
            success_count, error_count, errors = import_patients_from_csv(file_path, current_user.id)
            
            # Remove the file after processing
            os.remove(file_path)
            
            if success_count > 0:
                flash(f'Successfully imported {success_count} patient(s)!', 'success')
            
            if error_count > 0:
                flash(f'Failed to import {error_count} patient(s). See details below.', 'warning')
                for error in errors[:5]:  # Only show the first 5 errors to avoid cluttering the page
                    flash(error, 'danger')
                if len(errors) > 5:
                    flash(f'...and {len(errors) - 5} more errors.', 'danger')
            
            return redirect(url_for('dashboard'))
    
    return render_template('import_patients.html', title='Import Patients')

@app.route('/patient/<int:patient_id>/add_genotype', methods=['GET', 'POST'])
@login_required
def add_genotype_data(patient_id):
    """Route for adding genotype data for a patient"""
    patient = Patient.query.get_or_404(patient_id)
    
    # Ensure the current user is the provider for this patient
    if patient.provider_id != current_user.id:
        flash('You do not have permission to add genotype data for this patient.', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        gene = request.form.get('gene')
        variant = request.form.get('variant')
        phenotype = request.form.get('phenotype')
        significance = request.form.get('significance')
        
        # Create a new genotype data record
        new_genotype = GenotypeData(
            gene=gene,
            variant=variant,
            phenotype=phenotype,
            significance=significance,
            patient_id=patient.id
        )
        
        db.session.add(new_genotype)
        db.session.commit()
        
        flash('Genotype data added successfully!', 'success')
        return redirect(url_for('view_genotype_data', patient_id=patient.id))
    
    return render_template('add_genotype.html', title='Add Genotype Data', patient=patient)

@app.route('/patient/<int:patient_id>/genotype')
@login_required
def view_genotype_data(patient_id):
    """Route for viewing genotype data for a patient"""
    patient = Patient.query.get_or_404(patient_id)
    
    # Ensure the current user is the provider for this patient
    if patient.provider_id != current_user.id:
        flash('You do not have permission to view genotype data for this patient.', 'danger')
        return redirect(url_for('dashboard'))
    
    genotype_data = GenotypeData.query.filter_by(patient_id=patient.id).all()
    genotype_analyses = GenotypeAnalysis.query.filter_by(patient_id=patient.id).all()
    
    return render_template(
        'genotype_data.html', 
        title='Genotype Data', 
        patient=patient, 
        genotype_data=genotype_data,
        genotype_analyses=genotype_analyses
    )

@app.route('/patient/<int:patient_id>/analyze_genotype', methods=['POST'])
@login_required
def analyze_genotype(patient_id):
    """Route for analyzing genotype data for drug metabolism using Google's Gemini API"""
    patient = Patient.query.get_or_404(patient_id)
    
    # Ensure the current user is the provider for this patient
    if patient.provider_id != current_user.id:
        flash('You do not have permission to analyze genotype data for this patient.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Check if Google API key is set
    if not os.environ.get('GOOGLE_API_KEY'):
        flash('Google API key is not configured. Please contact the administrator.', 'danger')
        return redirect(url_for('view_genotype_data', patient_id=patient.id))
    
    drug_name = request.form.get('drug_name')
    rxcui = get_rxcui_for_name(drug_name)
    
    # Get genotype data for the patient
    genotype_data_dict = get_genotype_data_for_patient(patient.id)
    
    if not genotype_data_dict:
        flash('No genotype data available for this patient. Please add genotype data first.', 'warning')
        return redirect(url_for('view_genotype_data', patient_id=patient.id))
    
    # Analyze genotype data for drug metabolism using Google's Gemini API
    analysis_result = analyze_drug_metabolism(genotype_data_dict, drug_name)
    
    if 'error' in analysis_result and analysis_result['error'] != 'API key not configured':
        flash(f"Error during analysis: {analysis_result['error']}", 'danger')
        return redirect(url_for('view_genotype_data', patient_id=patient.id))
    
    # Store analysis results in the database
    new_analysis = GenotypeAnalysis(
        drug_name=drug_name,
        rxcui=rxcui,
        metabolism_effect=analysis_result.get('metabolism_effect', 'unknown'),
        recommendations=analysis_result.get('recommendations', ''),
        explanation=analysis_result.get('explanation', ''),
        full_analysis=analysis_result.get('full_analysis', ''),
        citations=json.dumps(analysis_result.get('citations', [])),
        patient_id=patient.id
    )
    
    db.session.add(new_analysis)
    db.session.commit()
    
    flash('Genotype analysis completed successfully!', 'success')
    return redirect(url_for('view_analysis_result', analysis_id=new_analysis.id))

@app.route('/genotype_analysis/<int:analysis_id>')
@login_required
def view_analysis_result(analysis_id):
    """Route for viewing genotype analysis results"""
    analysis = GenotypeAnalysis.query.get_or_404(analysis_id)
    patient = Patient.query.get_or_404(analysis.patient_id)
    
    # Ensure the current user is the provider for this patient
    if patient.provider_id != current_user.id:
        flash('You do not have permission to view this analysis.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Parse citations if available
    citations = []
    if analysis.citations:
        try:
            citations = json.loads(analysis.citations)
        except json.JSONDecodeError:
            logging.error(f"Error parsing citations JSON for analysis {analysis_id}")
    
    return render_template(
        'genotype_analysis.html', 
        title='Genotype Analysis Result', 
        patient=patient, 
        analysis=analysis,
        citations=citations
    )
