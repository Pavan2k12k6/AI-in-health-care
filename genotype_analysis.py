import os
import json
import logging
import google.generativeai as genai

def analyze_drug_metabolism(genotype_data, drug_name):
    """
    Analyze how a patient's genotype might affect metabolism of a specific drug using Google's Gemini API
    
    Args:
        genotype_data (dict): Patient's genotype data (gene variants)
        drug_name (str): Name of the drug to analyze
        
    Returns:
        dict: Analysis results including metabolism effect, recommendations, and explanation
    """
    try:
        api_key = os.environ.get('GOOGLE_API_KEY')
        if not api_key:
            logging.error("Missing Google API key")
            return {
                "error": "API key not configured",
                "metabolism_effect": "unknown",
                "recommendations": "Cannot analyze without API access. Please contact administrator.",
                "explanation": "No data available"
            }
        
        # Configure the Gemini API
        genai.configure(api_key=api_key)
        
        # Format the genotype data into a readable format for the prompt
        genotype_str = "\n".join([f"{gene}: {variant}" for gene, variant in genotype_data.items()])
        
        # Create a well-structured prompt for the Gemini model
        prompt = f"""You are a pharmacogenomics expert analyzing how genetic variations affect drug metabolism.

Based on the following patient genetic variants, analyze how they might affect the metabolism of {drug_name}:

Patient Genotype:
{genotype_str}

Please provide:
1. The overall predicted metabolism effect (ultrarapid, rapid, normal, intermediate, or poor)
2. Clinical implications and dosage recommendations
3. A brief explanation of which gene variants are most relevant to this drug
4. Any known potential adverse effects based on this genetic profile

Use established pharmacogenomic databases and research in your analysis.
"""
        
        # Get a response from the generative model
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        
        if response:
            analysis_text = response.text
            
            # Parse the analysis text to extract structured data
            # This is a simplified parsing - a more robust implementation would use regex or better parsing
            metabolism_effect = "normal"  # Default value
            if "ultrarapid" in analysis_text.lower():
                metabolism_effect = "ultrarapid"
            elif "rapid" in analysis_text.lower():
                metabolism_effect = "rapid"
            elif "intermediate" in analysis_text.lower():
                metabolism_effect = "intermediate"
            elif "poor" in analysis_text.lower():
                metabolism_effect = "poor"
                
            # Extract recommendations as everything after "recommendations" or similar keywords
            recommendations = analysis_text
            explanation = analysis_text
            
            # Return structured analysis
            return {
                "metabolism_effect": metabolism_effect,
                "recommendations": recommendations,
                "explanation": explanation,
                "full_analysis": analysis_text,
                "citations": []  # Gemini doesn't provide citations in the same format as Perplexity
            }
        else:
            logging.error("No response from Gemini API")
            return {
                "error": "No response from AI model",
                "metabolism_effect": "unknown",
                "recommendations": "Error analyzing genotype data.",
                "explanation": "API service unavailable"
            }
            
    except Exception as e:
        logging.error(f"Error in genotype analysis: {str(e)}")
        return {
            "error": str(e),
            "metabolism_effect": "unknown",
            "recommendations": "Error analyzing genotype data.",
            "explanation": "Analysis service error"
        }