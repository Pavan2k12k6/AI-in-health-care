import requests
import logging
import os
from urllib.parse import quote

# RxNav API base URL
RXNAV_API_BASE = "https://rxnav.nlm.nih.gov/REST"

def get_rxcui_for_name(drug_name):
    """
    Get RxCUI (RxNorm Concept Unique Identifier) for a drug name
    """
    try:
        url = f"{RXNAV_API_BASE}/rxcui.json?name={quote(drug_name)}"
        response = requests.get(url)
        data = response.json()
        
        if response.status_code == 200 and 'idGroup' in data and 'rxnormId' in data['idGroup'] and data['idGroup']['rxnormId']:
            return data['idGroup']['rxnormId'][0]
        else:
            logging.warning(f"Could not find RxCUI for {drug_name}")
            return None
            
    except Exception as e:
        logging.error(f"Error getting RxCUI for {drug_name}: {str(e)}")
        return None

def check_interactions(rxcui1, rxcui2):
    """
    Check for interactions between two drugs using their RxCUIs
    Returns a list of interaction objects or an empty list if none found
    """
    try:
        # Construct the URL for interaction API
        url = f"{RXNAV_API_BASE}/interaction/list.json?rxcuis={rxcui1}+{rxcui2}"
        response = requests.get(url)
        data = response.json()
        
        interactions = []
        
        if (response.status_code == 200 and 
            'fullInteractionTypeGroup' in data and 
            data['fullInteractionTypeGroup']):
            
            for group in data['fullInteractionTypeGroup']:
                if 'fullInteractionType' in group:
                    for interaction_type in group['fullInteractionType']:
                        if 'interactionPair' in interaction_type:
                            for pair in interaction_type['interactionPair']:
                                if 'description' in pair:
                                    # Determine severity based on keywords in description
                                    severity = determine_severity(pair['description'])
                                    
                                    # Generate recommendation based on severity
                                    recommendation = generate_recommendation(severity, pair['description'])
                                    
                                    interactions.append({
                                        'description': pair['description'],
                                        'severity': severity,
                                        'source': group.get('sourceName', 'RxNav'),
                                        'recommendation': recommendation
                                    })
        
        return interactions
        
    except Exception as e:
        logging.error(f"Error checking interactions between {rxcui1} and {rxcui2}: {str(e)}")
        return []

def determine_severity(description):
    """
    Determine the severity of an interaction based on the description
    """
    description_lower = description.lower()
    
    # Severe keywords
    if any(kw in description_lower for kw in [
        'contraindicated', 'life-threatening', 'fatal', 'death', 'severe', 
        'significant', 'serious', 'major', 'dangerous'
    ]):
        return 'severe'
    
    # Moderate keywords
    elif any(kw in description_lower for kw in [
        'moderate', 'monitor closely', 'may increase', 'may decrease',
        'adjust dose', 'potential', 'caution'
    ]):
        return 'moderate'
    
    # Mild keywords
    elif any(kw in description_lower for kw in [
        'mild', 'minor', 'minimal', 'unlikely', 'rare', 'slight'
    ]):
        return 'mild'
    
    # Default
    else:
        return 'moderate'  # Default to moderate if can't determine

def generate_recommendation(severity, description):
    """
    Generate a recommendation based on severity and description
    """
    if severity == 'severe':
        return "CAUTION: Consider alternative medication or do not co-administer. Close monitoring required if no alternatives available."
    
    elif severity == 'moderate':
        return "Monitor patient closely. Consider dose adjustment or timing changes to minimize interaction."
    
    elif severity == 'mild':
        return "Be aware of potential interaction. Normal monitoring should be sufficient."
    
    else:
        return "Use clinical judgment. Refer to specific interaction details for guidance."
