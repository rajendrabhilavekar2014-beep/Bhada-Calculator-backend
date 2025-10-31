# app.py file ka content

import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

# Zaroori: load_dotenv() ko sabse upar rakhiye
from dotenv import load_dotenv
load_dotenv() 

# --- SERVER INITIALIZATION ---
app = Flask(__name__)
# Nayi CORS configuration: Sirf aapki Netlify site ko allow karega
CORS(app, resources={r"/*": {"origins": "https://venerable-treacle-e62878.netlify.app"}})

GOOGLE_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
BASE_URL = "https://maps.googleapis.com/maps/api"

# *** Internal Databases ***
TRUCK_MILEAGE_DB = {"TATA 1618": 4.5, "ASHOK LEYLAND ECOMET": 4.0, "OTHER": 3.8} 
FUEL_RATE_DB = {"Maharashtra": 93.00, "Gujarat": 92.50} # Example rates
STATE_ENTRY_TAX_DB = {"Gujarat": 1000, "Madhya Pradesh": 1500, "Rajasthan": 1200}
BASE_FREIGHT_RATE_DB = {"NORMAL": 3.50, "PREMIUM": 4.50} # Rate per ton-km
DEFAULT_CHARGES = {"driver_daily_charge": 800, "loading_unloading_cost": 500}

# --- FUNCTIONS ---

def get_route_info(origin, destination):
    # API calls using GOOGLE_API_KEY here
    # ... (Yeh function abhi dummy/simple data dega)
    return {"distance_km": 500, "toll_cost": 3500} 

def calculate_costs(info, load_weight, truck_model):
    # ... (cost calculation logic)
    distance = info['distance_km']
    toll = info['toll_cost']
    
    # Simple Cost Logic for Demo
    mileage = TRUCK_MILEAGE_DB.get(truck_model, TRUCK_MILEAGE_DB['OTHER'])
    fuel_cost_per_liter = FUEL_RATE_DB.get("Maharashtra", 93.00) # Simplified fuel assumption
    
    total_fuel_needed = distance / mileage
    fuel_cost = total_fuel_needed * fuel_cost_per_liter
    
    total_costs = fuel_cost + toll + DEFAULT_CHARGES['driver_daily_charge']
    
    return {"fuel": round(fuel_cost, 0), "toll": toll, "total_trip_cost": round(total_costs, 0)}

# --- API ROUTE ---

@app.route("/calculate_bhada", methods=["POST"])
def calculate_bhada():
    try:
        data = request.get_json()
        origin = data.get("origin")
        destination = data.get("destination")
        load_weight_tons = data.get("load_weight_tons", 10)
        truck_model = data.get("truck_model", "OTHER")
        material_type = data.get("material_type", "NORMAL")
        
        # 1. Route Info
        route_info = get_route_info(origin, destination) 
        
        # 2. Cost Calculation
        costs = calculate_costs(route_info, load_weight_tons, truck_model)
        
        # 3. Income Calculation
        freight_rate = BASE_FREIGHT_RATE_DB.get(material_type, BASE_FREIGHT_RATE_DB['NORMAL'])
        base_freight_income = freight_rate * load_weight_tons * route_info['distance_km']
        
        # 4. Final Quote (Income - Costs + Profit Margin)
        # Simplified: Base Freight + Toll + Entry Tax (assuming a small profit margin is baked in)
        entry_tax = STATE_ENTRY_TAX_DB.get(data.get("destination_state", "Gujarat"), 0)
        
        final_bhada = round(base_freight_income + costs['toll'] + entry_tax, 0)
        
        return jsonify({
            "final_bhada_quote": final_bhada,
            "base_freight_income": round(base_freight_income, 0),
            "distance_km": route_info['distance_km'],
            "cost_breakdown": {
                "fuel": costs['fuel'],
                "toll": costs['toll'],
                "total_expenses": costs['total_trip_cost'],
                "entry_tax": entry_tax
            }
        })
        
    except Exception as e:
        return jsonify({"error": str(e), "message": "An error occurred during calculation."}), 500

if __name__ == '__main__':
    app.run(debug=True)
    
