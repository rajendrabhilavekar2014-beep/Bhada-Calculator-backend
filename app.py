# app.py file ka content
import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv 
from flask_cors import CORS 
import requests

load_dotenv() 
app = Flask(__name__)
CORS(app) 

GOOGLE_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY") 
BASE_URL = "https://maps.googleapis.com/maps/api/"

# ***************************************************************
# *** Internal Databases ***
# ***************************************************************
TRUCK_MILEAGE_DB = {"TATA 1618": 4.5, "ASHOK LEYLAND ECOMET": 5.0, "BHARAT BENZ 1623C": 4.0, "OTHER": 4.2}
FUEL_RATE_DB = {"Maharashtra": 93.00, "Gujarat": 92.50, "Delhi": 90.00, "DEFAULT": 91.50}
STATE_ENTRY_TAX_DB = {"Gujarat": 1000, "Madhya Pradesh": 1500, "Maharashtra": 800, "DEFAULT_INTERSTATE_TAX": 1200}
BASE_FREIGHT_RATE_DB = {"NORMAL": 3.50, "PREMIUM": 5.00}
DEFAULT_CHARGES = {"driver_daily_charge": 800, "loading_unloading_charge": 2500, "misc_expenses": 500}

def get_route_and_toll_details(origin, destination):
    if not GOOGLE_API_KEY:
        return {"distance_km": 650.0, "duration_hours": 11.0, "toll_charges_inr": 650, "source": origin, "destination": destination}
    
    distance_endpoint = f"{BASE_URL}distancematrix/json?units=metric&origins={origin}&destinations={destination}&key={GOOGLE_API_KEY}"
    
    try:
        distance_response = requests.get(distance_endpoint)
        distance_data = distance_response.json()
        
        if distance_data.get('status') != 'OK' or not distance_data['rows'][0]['elements'][0].get('distance'):
             return {"distance_km": 650.0, "duration_hours": 11.0, "toll_charges_inr": 650, "source": origin, "destination": destination}

        distance_km = distance_data['rows'][0]['elements'][0]['distance']['value'] / 1000
        duration_seconds = distance_data['rows'][0]['elements'][0]['duration']['value']
        estimated_toll = int(distance_km / 100 * 100) 
        
        return {"distance_km": round(distance_km, 2), "duration_hours": round(duration_seconds / 3600, 1), "toll_charges_inr": estimated_toll, "source": origin, "destination": destination}
    
    except Exception as e:
        return {"error": f"Distance/Toll calculation mein error: {e}"}

def calculate_fuel_cost(distance_km, truck_model, destination_state, manual_mileage=None, manual_fuel_rate=None):
    if manual_mileage is not None and manual_mileage > 0:
        mileage_kpl = manual_mileage
    else:
        mileage_kpl = TRUCK_MILEAGE_DB.get(truck_model.upper(), TRUCK_MILEAGE_DB["OTHER"])
        
    if manual_fuel_rate is not None and manual_fuel_rate > 0:
        fuel_rate_inr = manual_fuel_rate
    else:
        fuel_rate_inr = FUEL_RATE_DB.get(destination_state.title(), FUEL_RATE_DB["DEFAULT"])

    try:
        required_fuel_litres = distance_km / mileage_kpl
        total_fuel_cost = required_fuel_litres * fuel_rate_inr
    except ZeroDivisionError:
        required_fuel_litres = 0
        total_fuel_cost = 0
        
    return {"mileage_kpl": mileage_kpl, "fuel_rate_inr": fuel_rate_inr, "total_fuel_cost_inr": round(total_fuel_cost)}

def calculate_total_bhada(route_details, fuel_details, trip_info, driver_manual_charges):
    total_fuel_cost = fuel_details['total_fuel_cost_inr']
    total_toll_cost = route_details['toll_charges_inr']
    state_tax_rate = STATE_ENTRY_TAX_DB.get(trip_info.get('destination_state', 'DEFAULT'), STATE_ENTRY_TAX_DB['DEFAULT_INTERSTATE_TAX'])
    state_changes = trip_info.get('state_changes', 1)
    total_state_tax = state_changes * state_tax_rate
    driver_charges = driver_manual_charges.get('driver_charge', DEFAULT_CHARGES['driver_daily_charge'])
    labour_charges = driver_manual_charges.get('loading_unloading', DEFAULT_CHARGES['loading_unloading_charge'])
    other_charges = driver_manual_charges.get('misc_expenses', DEFAULT_CHARGES['misc_expenses'])
    total_operating_cost = total_fuel_cost + total_toll_cost + total_state_tax + driver_charges + labour_charges + other_charges
    material_risk = trip_info.get('material_type', 'NORMAL').upper()
    base_rate_per_ton_km = BASE_FREIGHT_RATE_DB['PREMIUM'] if material_risk in ["COSTLY", "FRAGILE"] else BASE_FREIGHT_RATE_DB['NORMAL']
    distance_km = route_details['distance_km']
    load_weight_tons = trip_info.get('load_weight_tons', 10)
    base_freight = distance_km * load_weight_tons * base_rate_per_ton_km
    final_quotation_bhada = total_operating_cost + base_freight
    
    return {"final_bhada_quote": round(final_quotation_bhada), "base_freight_income": round(base_freight), "total_operating_cost": round(total_operating_cost), "cost_breakdown": {"fuel": round(total_fuel_cost), "toll": round(total_toll_cost), "state_tax": round(total_state_tax), "driver_charge": driver_charges, "labour_charge": labour_charges, "other_expenses": other_charges}}

@app.route('/calculate_bhada', methods=['POST'])
def calculate():
    data = request.get_json()
    origin = data.get('origin')
    destination = data.get('destination')
    
    if not origin or not destination:
        return jsonify({"error": "Origin aur Destination zaroori hain."}), 400

    user_inputs = {'truck_model': data.get('truck_model', 'OTHER'), 'destination_state': data.get('destination_state', '').strip(), 'load_weight_tons': data.get('load_weight_tons', 10), 'material_type': data.get('material_type', 'NORMAL'), 'state_changes': data.get('state_changes', 1), 'manual_mileage': data.get('manual_mileage'), 'manual_fuel_rate': data.get('manual_fuel_rate')}
    driver_manual_charges = {'driver_charge': data.get('driver_charge'), 'loading_unloading': data.get('loading_unloading'), 'misc_expenses': data.get('misc_expenses')}

    route_details = get_route_and_toll_details(origin, destination)
    if "error" in route_details:
        return jsonify(route_details), 500

    fuel_details = calculate_fuel_cost(route_details['distance_km'], user_inputs['truck_model'], user_inputs['destination_state'], user_inputs['manual_mileage'], user_inputs['manual_fuel_rate'])
    final_result = calculate_total_bhada(route_details, fuel_details, user_inputs, driver_manual_charges)

    return jsonify(final_result) 

if __name__ == '__main__':
    app.run(debug=True, port=5000)
