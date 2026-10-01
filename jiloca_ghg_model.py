#!/usr/bin/env python3
"""All-sector greenhouse-gas model for the Jiloca distributed-compute corridor (Teruel, Spain).

Single source of truth. Every parameter (p_*) and every calculation (c_*) is defined once here.
The same expressions are evaluated in Python (this file) and mirrored in the supplied source-data
workbook for audit; the machine-readable CSV outputs are generated directly from this model.

Boundaries
  A  Territorial: household electricity, space heating, cooking, mobility, farm machinery,
     livestock (enteric + manure-management methane) and the compute load itself.
  B  Value chain (substitution): alfalfa dehydration and haulage, feed switching, greenhouse
     vegetables, aquaculture, bread, residents' beef and cheese supply chains.

Compute counterfactual
  The reference places the same IT load in one mega-campus with the SAME electricity procurement
  and the SAME PUE, and rejects its heat. The only compute-side differences are the inter-site
  network and the heat-network lift electricity; the architectural signal appears where the heat
  is used (district heating, alfalfa drying, greenhouse, aquaculture, bread proving).

Units: energy GWh unless stated; emissions tCO2e/yr; CH4 converted with AR6 GWP100 (non-fossil).
Prospective screening model. Nothing here is an achieved outcome.
"""
from __future__ import annotations
import csv, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.join(HERE, "model_outputs")

# ------------------------------------------------------------------ nodes
# name, residents (INE, as on jardinesdigitales.es/la-red.html; Singra INE 2025), IT MW (project design),
# municipal area km2 (INE via infolaso.com), lat, lon, hydrological zone
NODES = [
    ("Cella", 2702, 11.80, 124.68, 40.450000, -1.283333, "Fuente de Cella"),
    ("Villarquemado", 901, 3.93, 56.43, 40.517680, -1.267680, "Fuente de Cella"),
    ("Santa Eulalia del Campo", 1004, 4.38, 80.97, 40.566700, -1.316700, "Fuente de Cella"),
    ("Torremocha–Torrelacárcel–Alba (shared node)", 432, 3.10, 139.01, 40.590500, -1.297100, "Fuente de Cella"),
    ("Singra (prototype)", 76, 1.02, 36.72, 40.655641, -1.311867, "Fuente de Cella"),
    ("Villafranca del Campo", 290, 1.27, 66.55, 40.694167, -1.346111, "Fuente de Cella"),
    ("Monreal del Campo", 2578, 11.26, 89.05, 40.789444, -1.353611, "Ojos de Monreal"),
    ("Torrijo del Campo", 501, 2.20, 44.04, 40.825000, -1.337778, "Ojos de Monreal"),
    ("Caminreal", 617, 2.70, 44.39, 40.838611, -1.320833, "Ojos de Caminreal–Jiloca"),
    ("Fuentes Claras", 428, 1.90, 36.91, 40.863611, -1.323611, "Ojos de Caminreal–Jiloca"),
    ("Calamocha", 4655, 20.40, 316.63, 40.916667, -1.300000, "Ojos de Caminreal–Jiloca"),
]

# ------------------------------------------------------------------ parameters
# (name, value, unit, group, source/basis)
P = [
    # source-workbook scaling bases (eight-municipality community carbon model)
    ("p_pop_src", 8185, "people", "Scaling", "Source community model (8 municipalities)"),
    ("p_hh_src", 3461, "households", "Scaling", "Source community model"),
    ("p_dh_src", 2847, "households", "Scaling", "Source community model; district-heated share preserved"),
    ("p_veh_src", 4037, "vehicles", "Scaling", "Source community model"),
    # household services
    ("p_elec_hh", 2731.6, "kWh/household-yr", "Households", "Source community model"),
    ("p_heat_hh", 18050, "kWh useful heat/household-yr", "Households", "Source community model"),
    ("p_cook_hh", 1500, "kWh useful/household-yr", "Households", "Source community model"),
    ("p_eff_cook", 0.90, "fraction", "Households", "Source community model (gas appliance)"),
    ("p_eff_induction", 0.85, "fraction", "Households", "Screening assumption"),
    # reference heating mix (rural Teruel, screening; sensitivity tested)
    ("p_mix_oil", 0.60, "share of useful heat", "Reference heating", "Screening assumption: heating oil (gasóleo C) dominant off the gas grid"),
    ("p_mix_lpg", 0.15, "share", "Reference heating", "Screening assumption"),
    ("p_mix_ng", 0.15, "share", "Reference heating", "Screening assumption: gas grid in larger towns"),
    ("p_mix_bio", 0.10, "share", "Reference heating", "Screening assumption: wood/pellet"),
    ("p_cook_mix_lpg", 0.70, "share", "Reference heating", "Screening assumption: bottled butane/propane"),
    ("p_eff_oil", 0.85, "fraction", "Reference heating", "Screening boiler efficiency"),
    ("p_eff_lpg", 0.90, "fraction", "Reference heating", "Screening boiler efficiency"),
    ("p_eff_ng", 0.90, "fraction", "Reference heating", "Source community model"),
    ("p_eff_bio", 0.75, "fraction", "Reference heating", "Screening stove/boiler efficiency"),
    # fuel emission factors (combustion, kg CO2/kWh NCV) and well-to-tank uplifts
    ("p_ef_oil", 0.26676, "kgCO2/kWh fuel", "Fuel factors", "74.10 kgCO2/GJ, Spain NIR 2024 Annex 7 (gas oil)"),
    ("p_ef_lpg", 0.22716, "kgCO2/kWh fuel", "Fuel factors", "63.10 kgCO2/GJ, Spain NIR 2024 Annex 7 (LPG)"),
    ("p_ef_ng", 0.20156, "kgCO2/kWh fuel", "Fuel factors", "55.99 kgCO2/GJ, Spain NIR 2024 Annex 7 (natural gas)"),
    ("p_ef_biomass", 0.03, "kgCO2e/kWh fuel", "Fuel factors", "Screening non-CO2 and supply-chain factor; biogenic CO2 excluded"),
    ("p_wtt_oil", 1.25, "× combustion", "Fuel factors", "Screening well-to-tank uplift for oil products (heating oil, diesel); same value as the source model uses for gasoline"),
    ("p_wtt_lpg", 1.12, "× combustion", "Fuel factors", "Screening well-to-tank uplift"),
    ("p_wtt_ng", 1.20, "× combustion", "Fuel factors", "Screening well-to-tank uplift incl. supply-chain methane"),
    ("p_ef_hvo", 0.0576, "kgCO2e/kWh fuel", "Fuel factors", "16 gCO2e/MJ renewable diesel/heating oil from wastes (83% below the 94 gCO2e/MJ RED II comparator)"),
    ("p_ef_biomethane", 0.010, "kgCO2e/kWh fuel", "Fuel factors", "Screening upgrading/compression factor; leakage counted separately"),
    ("p_diesel_kwh_l", 9.972, "kWh/L", "Fuel factors", "43.0 GJ/t × 0.835 kg/L"),
    # electricity
    ("p_ef_grid_mb", 0.258, "kgCO2e/kWh", "Electricity", "MITECO 2025 national mix without guarantees of origin (market-based reference)"),
    ("p_ef_grid_lb", 0.215, "kgCO2e/kWh", "Electricity", "Spanish system operational intensity 2025 (location-based)"),
    ("p_ef_own", 0.02, "kgCO2e/kWh", "Electricity", "Screening lifecycle factor, wind and solar"),
    ("p_ef_ppa", 0.02, "kgCO2e/kWh", "Electricity", "Screening lifecycle factor, residual renewable PPA (annual matching)"),
    ("p_wind_per_it", 90 / 35.74, "MW wind/MW IT", "Electricity", "Six-site design: 90 MW wind for 35.74 MW IT"),
    ("p_solar_per_it", 30 / 35.74, "MWp/MW IT", "Electricity", "Six-site design: 30 MWp solar for 35.74 MW IT"),
    ("p_wind_cf", 0.3115677321156773, "fraction", "Electricity", "Source community model"),
    ("p_solar_cf", 0.20, "fraction", "Electricity", "Source community model"),
    # mobility
    ("p_km_veh", 12000, "km/vehicle-yr", "Mobility", "Source community model"),
    ("p_l100", 7.5, "L/100 km", "Mobility", "Source community model"),
    ("p_gasoline_kg_l", 2.347, "kgCO2/L", "Mobility", "Source community model"),
    ("p_wtt_gasoline", 1.25, "× tailpipe", "Mobility", "Source community model"),
    ("p_bev_share", 0.90, "share", "Mobility", "Project design (≈89.5% BEV)"),
    ("p_phev_share", 0.10, "share", "Mobility", "Project design"),
    ("p_phev_efrac", 0.60, "share of km", "Mobility", "Source community model"),
    ("p_bev_kwh_km", 0.18, "kWh/km", "Mobility", "Source community model"),
    ("p_charge_loss", 0.10, "fraction", "Mobility", "Screening charging loss"),
    ("p_rgas_ratio", 0.2717391304347826, "× fossil WTW", "Mobility", "Source community model renewable-gasoline ratio"),
    ("p_bus_km", 250000, "km/yr", "Mobility", "Screening: free inter-municipal electric bus (added service, no reference credit)"),
    ("p_bus_kwh_km", 1.3, "kWh/km", "Mobility", "Screening"),
    # compute and heat
    ("p_pue", 1.150, "ratio", "Compute", "Project design, liquid-cooled halls"),
    ("p_pue_campus", 1.150, "ratio", "Compute", "Mega-campus reference: same PUE (neutral); sensitivity 1.10–1.45"),
    ("p_net_frac", 0.01, "fraction of IT energy", "Compute", "Inter-site network allowance; sensitivity 0.5–3%"),
    ("p_heat_recovery", 0.88, "fraction of IT energy", "Compute", "Project design, liquid-loop capture"),
    ("p_dh_lift_share", 7.3 / 51.4, "kWhe/kWhth delivered", "Compute", "Project design heat-pump lift for district heating"),
    ("p_dh_pump", 0.015, "kWhe/kWhth", "Compute", "Source community model"),
    ("p_glass_ha", 42.89, "ha", "Compute", "Project design glasshouse area"),
    ("p_glass_gwh_ha", 30.1 / 23.9, "GWh/ha-yr", "Compute", "Project design heat demand"),
    ("p_seafood_t", 6559, "t/yr", "Compute", "Project design RAS output"),
    ("p_ras_mwh_t", 52.2 / 3665 * 1000, "MWh/t", "Compute", "Project design heat demand"),
    ("p_proving_kwh_kg", 0.2, "kWh/kg bread", "Compute", "Screening proving and baking-support heat"),
    ("p_ras_kwh_kg", 5.0, "kWh/kg", "Compute", "Screening RAS electricity (pumps, aeration, filtration); heat supplied separately"),
    ("p_glass_kwh_m2", 25, "kWh/m2-yr", "Compute", "Screening glasshouse electricity (climate control, irrigation; no supplementary lighting)"),
    ("p_dry_alf_gwh", 79.57, "GWh/yr", "Compute", "Project design: leased alfalfa dehydration line thermal duty"),
    ("p_dry_other_gwh", 37.33, "GWh/yr", "Compute", "Project design: owned high-value drying line (no credit taken)"),
    ("p_dry_lift_gwh", 15.6, "GWh/yr", "Compute", "Project design heat-pump lift for drying"),
    # farm machinery
    ("p_comarca_area_km2", 1932.10, "km2", "Agriculture", "Comarca del Jiloca"),
    ("p_comarca_cult_ha", 50734, "ha", "Agriculture", "Comarca del Jiloca cultivated area, 2009 (44,188 dry cereal + 3,651 irrigated + 2,179 legumes + 716 fruit)"),
    ("p_diesel_l_ha", 80, "L/ha-yr", "Agriculture", "Screening agricultural diesel intensity (project design)"),
    ("p_bio_tractor_cap", 0.30, "share of machinery energy", "Agriculture", "Screening cap on methane-tractor conversion"),
    # livestock (Comarca del Jiloca census 2009, area-scaled; replace with REGA municipal register)
    ("p_cattle_comarca", 2800, "head", "Livestock", "Comarca del Jiloca 2009"),
    ("p_sheep_comarca", 91000, "head", "Livestock", "Comarca del Jiloca 2009"),
    ("p_pigs_comarca", 187000, "head", "Livestock", "Comarca del Jiloca 2009"),
    ("p_goats_comarca", 773, "head", "Livestock", "Comarca del Jiloca 2009"),
    ("p_ent_cattle", 57, "kgCH4/head-yr", "Livestock", "IPCC 2006 Tier 1, Western Europe other cattle"),
    ("p_ent_sheep", 8, "kgCH4/head-yr", "Livestock", "IPCC 2006 Tier 1, developed countries"),
    ("p_ent_goat", 5, "kgCH4/head-yr", "Livestock", "IPCC 2006 Tier 1"),
    ("p_ent_pig", 1.5, "kgCH4/head-yr", "Livestock", "IPCC 2006 Tier 1, developed countries"),
    ("p_man_cattle", 6, "kgCH4/head-yr", "Livestock", "Screening Tier 1-type manure CH4, cool climate"),
    ("p_man_sheep", 0.19, "kgCH4/head-yr", "Livestock", "IPCC 2006 Tier 1"),
    ("p_man_goat", 0.13, "kgCH4/head-yr", "Livestock", "IPCC 2006 Tier 1"),
    ("p_man_pig", 6, "kgCH4/head-yr", "Livestock", "Screening Tier 1-type slurry CH4, cool climate"),
    ("p_gwp_ch4", 27.0, "kgCO2e/kgCH4", "Livestock", "IPCC AR6 GWP100, non-fossil methane"),
    ("p_cattle_fed_share", 0.70, "share of cattle-days", "Livestock", "Screening: share of cattle on a ration that can carry a daily additive"),
    ("p_additive_eff", 0.00, "fraction of enteric CH4", "Livestock", "No enteric-methane credit in the central case because the area-scaled cattle count is not disaggregated into animals covered by the current EU 3-NOP authorisation. Sensitivities include 30% 3-NOP efficacy on 70% of cattle-days and 80% Asparagopsis efficacy."),
    ("p_slurry_collect", 1.00, "share of pig slurry", "Livestock", "Project design requirement: all collectable pig slurry is routed promptly to the central anaerobic-digestion facility"),
    ("p_cattle_manure_collect", 0.50, "share of cattle manure", "Livestock", "Collectable/housed cattle-manure share; all manure in this share is routed to the central digester; pasture manure remains outside the collection boundary"),
    ("p_digest_avoid", 0.90, "fraction of routed-manure storage CH4 avoided", "Livestock", "Central high-quality gas-tight digester assumption; approximately the reduction implied by IPCC 2019 high-productivity anaerobic-digestion factors versus long-retention liquid/slurry storage in cool climates; sensitivity 0.80–0.95"),
    ("p_pig_vs", 0.30, "kg VS/head-day", "Livestock", "IPCC 2006 Tier 1, Western Europe swine"),
    ("p_pig_b0", 0.45, "m3 CH4/kg VS", "Livestock", "IPCC 2006 Tier 1"),
    ("p_cattle_vs", 2.6, "kg VS/head-day", "Livestock", "IPCC 2006 Tier 1, Western Europe other cattle"),
    ("p_cattle_b0", 0.18, "m3 CH4/kg VS", "Livestock", "IPCC 2006 Tier 1"),
    ("p_digester_yield", 0.60, "fraction of B0 realised", "Livestock", "Screening mesophilic digester performance"),
    ("p_ch4_kwh_m3", 9.97, "kWh/m3", "Livestock", "Methane lower heating value"),
    ("p_ch4_kg_m3", 0.717, "kg/m3", "Livestock", "Methane density at 0 °C"),
    ("p_leak", 0.03, "fraction of gross biogas CH4", "Livestock", "Central 3% additional methane loss for upgrading, compression and piping beyond the digester-management factor; sensitivity 1–6%. Together with residual managed-manure methane, this gives a central managed-manure/biomethane-chain methane residual of about 5.8% of gross methane production, close to the 5.4% mean measured across 31 European biogas plants by Olczak et al. (2026)."),
    ("p_pig_slurry_t_head_yr", 1.30, "t/head-yr", "Livestock logistics", "Screening midpoint of 1.1–1.5 m3/head-yr for finisher pig slurry in European/Spanish BAT literature; density approximated as 1 t/m3"),
    ("p_cattle_manure_t_head_yr", 7.30, "t/head-yr", "Livestock logistics", "Screening bovine manure production factor; applied only to the housed/collectable share"),
    ("p_slurry_haul_oneway_km", 20.0, "km", "Livestock logistics", "Screening average one-way haul to a corridor-scale central digester; requires farm-specific routing before field implementation"),
    # value chain
    ("p_alf_wet_t", 110600, "t/yr", "Value chain", "Project design: wilted alfalfa to the dehydration line (≈62% moisture implied by the water balance)"),
    ("p_alf_water_t", 63399, "t/yr", "Value chain", "Project design: water evaporated"),
    ("p_dryer_mj_kg", 4.0, "MJ fuel/kg water", "Value chain", "Reference gas-fired rotary-drum dehydrator specific fuel use (range 3.5–4.5)"),
    ("p_haul_ref_km", 300, "km", "Value chain", "Reference haul to Ebro-valley dehydrators (project website)"),
    ("p_haul_proj_km", 30, "km", "Value chain", "Project haul"),
    ("p_truck_kg_tkm", 0.09, "kgCO2e/t-km", "Value chain", "Smart Freight Centre GLEC Framework v3, Table 8: rounded European articulated-road-freight WTW screening factor (~0.089–0.095 kgCO2e/t-km depending vehicle/load)"),
    ("p_sbm_kg_day", 1.0, "kg/head-day", "Value chain", "Screening soybean meal replaced in supplementable cattle rations"),
    ("p_alf_per_sbm", 2.7, "kg alfalfa/kg SBM", "Value chain", "Crude-protein equivalence (~46% vs ~17% CP)"),
    ("p_ef_sbm", 1.5, "kgCO2e/kg", "Value chain", "Screening imported soybean meal incl. partial land-use change"),
    ("p_ef_alf", 0.10, "kgCO2e/kg", "Value chain", "Screening local alfalfa dried with recovered heat"),
    ("p_yield_kg_m2", 45, "kg/m2-yr", "Value chain", "Project design glasshouse yield"),
    ("p_ef_veg_ref", 0.70, "kgCO2e/kg", "Value chain", "Source community model"),
    ("p_ef_veg_proj", 0.25, "kgCO2e/kg", "Value chain", "Source community model"),
    ("p_ef_sea_ref", 10.0, "kgCO2e/kg", "Value chain", "Source community model"),
    ("p_ef_sea_proj", 3.0, "kgCO2e/kg", "Value chain", "Source community model"),
    ("p_bread_kg_hh", 96, "kg/household-yr", "Value chain", "Source community model"),
    ("p_ef_bread_ref", 1.0, "kgCO2e/kg", "Value chain", "Source community model"),
    ("p_ef_bread_proj", 0.5, "kgCO2e/kg", "Value chain", "Source community model"),
    ("p_beef_kg_pc", 3.9, "kg/person-yr", "Value chain", "Source community model"),
    ("p_cheese_kg_pc", 7.8, "kg/person-yr", "Value chain", "Source community model"),
    ("p_ef_beef", 60, "kgCO2e/kg", "Value chain", "Source community model"),
    ("p_ef_cheese", 22, "kgCO2e/kg", "Value chain", "Source community model"),
    ("p_beef_red", 0.3425, "fraction", "Value chain", "Source community model design case"),
    ("p_cheese_red", 0.5375, "fraction", "Value chain", "Source community model design case"),
]

# ------------------------------------------------------------------ calculations
# (name, expression, unit, sheet, description). Excel override for node sums via NODE_SUM.
C = [
    # scale
    ("c_pop", "NODE_SUM(pop)", "people", "Scale", "Residents, 13 municipalities"),
    ("c_it_mw", "NODE_SUM(mw)", "MW", "Scale", "Continuous IT load, 11 nodes"),
    ("c_area_km2", "NODE_SUM(area)", "km2", "Scale", "Municipal area, 13 municipalities"),
    ("c_hh", "ROUND(p_hh_src/p_pop_src*c_pop,0)", "households", "Scale", "Households, scaled"),
    ("c_dh_hh", "ROUND(p_dh_src/p_hh_src*c_hh,0)", "households", "Scale", "Households on district heating"),
    ("c_nondh_hh", "c_hh-c_dh_hh", "households", "Scale", "Households off district heating"),
    ("c_veh", "ROUND(p_veh_src/p_pop_src*c_pop,0)", "vehicles", "Scale", "Vehicles"),
    ("c_area_scale", "c_area_km2/p_comarca_area_km2", "ratio", "Scale", "Corridor/comarca area ratio (livestock and farmland proxy)"),
    # energy services
    ("c_heat_useful_gwh", "c_hh*p_heat_hh/1000000", "GWh", "Energy", "Useful space heat, all households"),
    ("c_dh_useful_gwh", "c_dh_hh*p_heat_hh/1000000", "GWh", "Energy", "Useful heat from recovered data-centre heat"),
    ("c_nondh_useful_gwh", "c_nondh_hh*p_heat_hh/1000000", "GWh", "Energy", "Useful heat off the heat network"),
    ("c_cook_useful_gwh", "c_hh*p_cook_hh/1000000", "GWh", "Energy", "Useful cooking energy"),
    ("c_cook_fuel_gwh", "c_cook_useful_gwh/p_eff_cook", "GWh", "Energy", "Cooking gas demand if all on gas"),
    ("c_hh_elec_gwh", "c_hh*p_elec_hh/1000000", "GWh", "Energy", "Household electricity"),
    ("c_veh_km", "c_veh*p_km_veh", "vehicle-km", "Energy", "Annual vehicle-km"),
    ("c_ev_elec_gwh", "c_veh_km*(p_bev_share+p_phev_share*p_phev_efrac)*p_bev_kwh_km*(1+p_charge_loss)/1000000", "GWh", "Energy", "Free charging electricity"),
    ("c_phev_fuel_l", "c_veh_km*p_phev_share*(1-p_phev_efrac)*p_l100/100", "L", "Energy", "Renewable gasoline, PHEV engine km"),
    ("c_bus_elec_gwh", "p_bus_km*p_bus_kwh_km/1000000", "GWh", "Energy", "Electric bus"),
    ("c_cult_ha", "p_comarca_cult_ha*c_area_scale", "ha", "Energy", "Cultivated area, area-scaled"),
    ("c_farm_diesel_l", "c_cult_ha*p_diesel_l_ha", "L", "Energy", "Farm machinery fuel"),
    ("c_farm_energy_gwh", "c_farm_diesel_l*p_diesel_kwh_l/1000000", "GWh", "Energy", "Farm machinery fuel energy"),
    ("c_bread_t", "c_hh*p_bread_kg_hh/1000", "t", "Energy", "Bread"),
    ("c_food_elec_gwh", "(p_seafood_t*p_ras_kwh_kg*1000+p_glass_ha*10000*p_glass_kwh_m2)/1000000", "GWh", "Energy", "Aquaculture and glasshouse electricity"),
    # compute and heat cascade
    ("c_it_gwh", "c_it_mw*8.76", "GWh", "Compute", "IT energy"),
    ("c_dc_gwh", "c_it_gwh*p_pue", "GWh", "Compute", "Facility electricity, distributed"),
    ("c_net_gwh", "c_it_gwh*p_net_frac", "GWh", "Compute", "Inter-site network electricity"),
    ("c_recoverable_gwh", "c_it_gwh*p_heat_recovery", "GWh", "Compute", "Recoverable heat at the liquid loop"),
    ("c_dh_lift_gwh", "c_dh_useful_gwh*p_dh_lift_share", "GWh", "Compute", "District-heating lift electricity"),
    ("c_dh_pump_gwh", "c_dh_useful_gwh*p_dh_pump", "GWh", "Compute", "District-heating pumping electricity"),
    ("c_glass_heat_gwh", "p_glass_ha*p_glass_gwh_ha", "GWh", "Compute", "Glasshouse heat"),
    ("c_ras_heat_gwh", "p_seafood_t*p_ras_mwh_t/1000", "GWh", "Compute", "Aquaculture heat"),
    ("c_proving_gwh", "c_bread_t*p_proving_kwh_kg/1000", "GWh", "Compute", "Bread proving heat"),
    ("c_dry_total_gwh", "p_dry_alf_gwh+p_dry_other_gwh", "GWh", "Compute", "Drying heat delivered"),
    ("c_dry_alf_lift_gwh", "p_dry_lift_gwh*p_dry_alf_gwh/c_dry_total_gwh", "GWh", "Compute", "Drying lift, alfalfa share"),
    ("c_dry_other_lift_gwh", "p_dry_lift_gwh-c_dry_alf_lift_gwh", "GWh", "Compute", "Drying lift, other line"),
    ("c_heat_used_gwh", "c_dh_useful_gwh+c_glass_heat_gwh+c_ras_heat_gwh+c_proving_gwh+c_dry_total_gwh", "GWh", "Compute", "Heat delivered to productive sinks"),
    ("c_heat_from_loop_gwh", "c_heat_used_gwh-c_dh_lift_gwh-p_dry_lift_gwh", "GWh", "Compute", "Of which drawn from the liquid loop"),
    ("c_heat_rejected_gwh", "c_recoverable_gwh-c_heat_from_loop_gwh", "GWh", "Compute", "Recoverable heat rejected"),
    ("c_erf", "c_heat_from_loop_gwh/(c_dc_gwh+c_dh_lift_gwh+p_dry_lift_gwh)", "fraction", "Compute", "Energy reuse factor (EN 50600-4-6 style)"),
    # livestock and biogas
    ("c_cattle", "p_cattle_comarca*c_area_scale", "head", "Livestock", "Cattle"),
    ("c_sheep", "p_sheep_comarca*c_area_scale", "head", "Livestock", "Sheep"),
    ("c_pigs", "p_pigs_comarca*c_area_scale", "head", "Livestock", "Pigs"),
    ("c_goats", "p_goats_comarca*c_area_scale", "head", "Livestock", "Goats"),
    ("c_ent_ch4_t", "(c_cattle*p_ent_cattle+c_sheep*p_ent_sheep+c_goats*p_ent_goat+c_pigs*p_ent_pig)/1000", "t CH4", "Livestock", "Enteric CH4"),
    ("c_man_ch4_t", "(c_cattle*p_man_cattle+c_sheep*p_man_sheep+c_goats*p_man_goat+c_pigs*p_man_pig)/1000", "t CH4", "Livestock", "Manure CH4"),
    ("c_additive_ch4_t", "c_cattle*p_ent_cattle*p_cattle_fed_share*p_additive_eff/1000", "t CH4", "Livestock", "Enteric CH4 avoided by feed additive"),
    ("c_digest_ch4_t", "(c_pigs*p_man_pig*p_slurry_collect+c_cattle*p_man_cattle*p_cattle_manure_collect)*p_digest_avoid/1000", "t CH4", "Livestock", "Reference manure-storage CH4 avoided by routing collectable pig slurry and housed cattle manure promptly to the gas-tight digester"),
    ("c_biogas_ch4_m3", "(c_pigs*p_slurry_collect*p_pig_vs*p_pig_b0+c_cattle*p_cattle_manure_collect*p_cattle_vs*p_cattle_b0)*365*p_digester_yield", "m3 CH4", "Livestock", "Gross methane produced from routed pig slurry and collectable cattle manure"),
    ("c_biomethane_gwh", "c_biogas_ch4_m3*p_ch4_kwh_m3/1000000", "GWh", "Livestock", "Biomethane energy"),
    ("c_leak_ch4_t", "c_biogas_ch4_m3*p_ch4_kg_m3*p_leak/1000", "t CH4", "Livestock", "Additional methane slip from upgrading, compression and piping beyond the digester-management factor"),
    ("c_slurry_pig_t", "c_pigs*p_slurry_collect*p_pig_slurry_t_head_yr", "t/yr", "Livestock logistics", "Pig slurry hauled to central digester"),
    ("c_slurry_cattle_t", "c_cattle*p_cattle_manure_collect*p_cattle_manure_t_head_yr", "t/yr", "Livestock logistics", "Collectable cattle manure hauled to central digester"),
    ("c_slurry_truck_t", "c_slurry_pig_t+c_slurry_cattle_t", "t/yr", "Livestock logistics", "Total wet manure transported"),
    ("c_slurry_truck_ef", "p_truck_kg_tkm*(p_ef_hvo/(p_ef_oil*p_wtt_oil))", "kgCO2e/t-km", "Livestock logistics", "Truck factor scaled from fossil freight to the modelled renewable-diesel lifecycle intensity"),
    ("c_slurry_truck_tco2", "c_slurry_truck_t*(2*p_slurry_haul_oneway_km)*c_slurry_truck_ef/1000", "tCO2e", "Livestock logistics", "Round-trip slurry/manure transport to central digester"),
    # biogas allocation (cooking → tractors up to cap → off-grid heating → surplus)
    ("c_bio_cook_gwh", "MIN(c_biomethane_gwh,c_cook_fuel_gwh)", "GWh", "Biogas", "Biomethane to cooking"),
    ("c_bio_farm_gwh", "MIN(c_biomethane_gwh-c_bio_cook_gwh,c_farm_energy_gwh*p_bio_tractor_cap)", "GWh", "Biogas", "Biomethane to farm machinery"),
    ("c_bio_heat_gwh", "MIN(c_biomethane_gwh-c_bio_cook_gwh-c_bio_farm_gwh,c_nondh_useful_gwh/p_eff_ng)", "GWh", "Biogas", "Biomethane to off-network heating"),
    ("c_bio_surplus_gwh", "c_biomethane_gwh-c_bio_cook_gwh-c_bio_farm_gwh-c_bio_heat_gwh", "GWh", "Biogas", "Surplus biomethane (no credit)"),
    ("c_cook_elec_gwh", "(c_cook_useful_gwh-c_bio_cook_gwh*p_eff_cook)/p_eff_induction", "GWh", "Biogas", "Induction cooking for the remainder"),
    ("c_farm_hvo_gwh", "c_farm_energy_gwh-c_bio_farm_gwh", "GWh", "Biogas", "Renewable diesel to farm machinery"),
    ("c_heat_hvo_gwh", "(c_nondh_useful_gwh-c_bio_heat_gwh*p_eff_ng)/p_eff_oil", "GWh", "Biogas", "Renewable heating oil off the heat network"),
    # electricity balance
    ("c_elec_hh_side_gwh", "c_hh_elec_gwh+c_ev_elec_gwh+c_bus_elec_gwh+c_cook_elec_gwh", "GWh", "Electricity", "Community electricity"),
    ("c_elec_food_gwh", "c_food_elec_gwh", "GWh", "Electricity", "Food-production electricity"),
    ("c_elec_heatnet_gwh", "c_dh_lift_gwh+c_dh_pump_gwh+p_dry_lift_gwh", "GWh", "Electricity", "Heat-network electricity"),
    ("c_elec_total_gwh", "c_elec_hh_side_gwh+c_elec_food_gwh+c_elec_heatnet_gwh+c_dc_gwh+c_net_gwh", "GWh", "Electricity", "Total project electricity"),
    ("c_own_gen_gwh", "c_it_mw*(p_wind_per_it*p_wind_cf+p_solar_per_it*p_solar_cf)*8.76", "GWh", "Electricity", "Own wind and solar"),
    ("c_own_used_gwh", "MIN(c_own_gen_gwh,c_elec_total_gwh)", "GWh", "Electricity", "Own generation used"),
    ("c_ppa_gwh", "c_elec_total_gwh-c_own_used_gwh", "GWh", "Electricity", "Residual renewable PPA"),
    ("c_own_share", "c_own_used_gwh/c_elec_total_gwh", "fraction", "Electricity", "Own-generation share"),
    ("c_ef_proj_mb", "(c_own_used_gwh*p_ef_own+c_ppa_gwh*p_ef_ppa)/c_elec_total_gwh", "kgCO2e/kWh", "Electricity", "Project intensity, market-based"),
    ("c_ef_proj_lb", "(c_own_used_gwh*p_ef_own+c_ppa_gwh*p_ef_grid_lb)/c_elec_total_gwh", "kgCO2e/kWh", "Electricity", "Project intensity, location-based"),
    # ---------------- emissions, reference (R) and project (J), tCO2e/yr
    ("R_elec", "c_hh_elec_gwh*p_ef_grid_mb*1000", "tCO2e", "Emissions", "Household electricity — reference"),
    ("J_elec", "c_hh_elec_gwh*c_ef_proj_mb*1000", "tCO2e", "Emissions", "Household electricity — project"),
    ("R_heat", "c_heat_useful_gwh*1000*(p_mix_oil*p_ef_oil*p_wtt_oil/p_eff_oil+p_mix_lpg*p_ef_lpg*p_wtt_lpg/p_eff_lpg+p_mix_ng*p_ef_ng*p_wtt_ng/p_eff_ng+p_mix_bio*p_ef_biomass/p_eff_bio)", "tCO2e", "Emissions", "Space heating — reference"),
    ("J_heat_dh", "(c_dh_lift_gwh+c_dh_pump_gwh)*c_ef_proj_mb*1000", "tCO2e", "Emissions", "Space heating from recovered heat — project"),
    ("J_heat_off", "(c_bio_heat_gwh*p_ef_biomethane+c_heat_hvo_gwh*p_ef_hvo)*1000", "tCO2e", "Emissions", "Space heating off network (biomethane, renewable heating oil) — project"),
    ("R_cook", "c_cook_fuel_gwh*1000*(p_cook_mix_lpg*p_ef_lpg*p_wtt_lpg+(1-p_cook_mix_lpg)*p_ef_ng*p_wtt_ng)", "tCO2e", "Emissions", "Cooking — reference"),
    ("J_cook", "(c_bio_cook_gwh*p_ef_biomethane+c_cook_elec_gwh*c_ef_proj_mb)*1000", "tCO2e", "Emissions", "Cooking — project"),
    ("R_mob", "c_veh_km*p_l100/100*p_gasoline_kg_l*p_wtt_gasoline/1000", "tCO2e", "Emissions", "Private mobility — reference"),
    ("J_mob", "(c_ev_elec_gwh+c_bus_elec_gwh)*c_ef_proj_mb*1000+c_phev_fuel_l*p_gasoline_kg_l*p_wtt_gasoline*p_rgas_ratio/1000", "tCO2e", "Emissions", "Mobility incl. free charging and bus — project"),
    ("R_farm", "c_farm_energy_gwh*p_ef_oil*p_wtt_oil*1000", "tCO2e", "Emissions", "Farm machinery — reference (gasóleo B)"),
    ("J_farm", "(c_bio_farm_gwh*p_ef_biomethane+c_farm_hvo_gwh*p_ef_hvo)*1000", "tCO2e", "Emissions", "Farm machinery — project"),
    ("R_ent", "c_ent_ch4_t*p_gwp_ch4", "tCO2e", "Emissions", "Enteric methane — reference"),
    ("J_ent", "(c_ent_ch4_t-c_additive_ch4_t)*p_gwp_ch4", "tCO2e", "Emissions", "Enteric methane — project"),
    ("R_man", "c_man_ch4_t*p_gwp_ch4", "tCO2e", "Emissions", "Manure methane — reference"),
    ("J_man", "(c_man_ch4_t-c_digest_ch4_t+c_leak_ch4_t)*p_gwp_ch4", "tCO2e", "Emissions", "Manure methane — project: unmanaged/pasture manure plus residual managed-manure emissions and biomethane-chain leakage"),
    ("J_slurry_transport", "c_slurry_truck_tco2", "tCO2e", "Emissions", "Renewable-fuel trucking of slurry/manure to the central digester"),
    ("R_compute", "c_it_gwh*p_pue_campus*c_ef_proj_mb*1000", "tCO2e", "Emissions", "Compute — mega-campus, same procurement"),
    ("J_compute", "(c_dc_gwh+c_net_gwh)*c_ef_proj_mb*1000", "tCO2e", "Emissions", "Compute — distributed network"),
    ("R_dry", "p_alf_water_t*p_dryer_mj_kg/3600*p_ef_ng*p_wtt_ng*1000", "tCO2e", "Emissions", "Alfalfa dehydration — reference gas-fired"),
    ("J_dry", "c_dry_alf_lift_gwh*c_ef_proj_mb*1000", "tCO2e", "Emissions", "Alfalfa dehydration with recovered heat — project"),
    ("J_dry_other", "c_dry_other_lift_gwh*c_ef_proj_mb*1000", "tCO2e", "Emissions", "Other drying line lift (no reference credit)"),
    ("c_alf_product_t", "p_alf_wet_t-p_alf_water_t", "t", "Emissions", "Dehydrated alfalfa output"),
    ("R_haul", "c_alf_product_t*p_haul_ref_km*p_truck_kg_tkm/1000", "tCO2e", "Emissions", "Alfalfa haulage — reference"),
    ("J_haul", "c_alf_product_t*p_haul_proj_km*p_truck_kg_tkm/1000", "tCO2e", "Emissions", "Alfalfa haulage — project"),
    ("c_sbm_t", "c_cattle*p_cattle_fed_share*p_sbm_kg_day*365/1000", "t", "Emissions", "Soybean meal displaced"),
    ("R_feed", "c_sbm_t*p_ef_sbm", "tCO2e", "Emissions", "Protein feed — reference soybean meal"),
    ("J_feed", "c_sbm_t*p_alf_per_sbm*p_ef_alf", "tCO2e", "Emissions", "Protein feed — local alfalfa"),
    ("c_veg_t", "p_glass_ha*10000*p_yield_kg_m2/1000", "t", "Emissions", "Glasshouse vegetables"),
    ("R_veg", "c_veg_t*p_ef_veg_ref", "tCO2e", "Emissions", "Vegetables — reference supply"),
    ("J_veg", "c_veg_t*p_ef_veg_proj+p_glass_ha*10000*p_glass_kwh_m2/1000000*c_ef_proj_mb*1000", "tCO2e", "Emissions", "Vegetables — corridor glasshouse"),
    ("R_sea", "p_seafood_t*p_ef_sea_ref", "tCO2e", "Emissions", "Seafood — reference supply"),
    ("J_sea", "p_seafood_t*p_ef_sea_proj+p_seafood_t*p_ras_kwh_kg/1000*c_ef_proj_mb*1000", "tCO2e", "Emissions", "Seafood — corridor RAS"),
    ("R_bread", "c_bread_t*p_ef_bread_ref", "tCO2e", "Emissions", "Bread — reference"),
    ("J_bread", "c_bread_t*p_ef_bread_proj", "tCO2e", "Emissions", "Bread — project"),
    ("R_beef", "c_pop*p_beef_kg_pc*p_ef_beef/1000", "tCO2e", "Emissions", "Residents' beef — reference"),
    ("J_beef", "R_beef*(1-p_beef_red)", "tCO2e", "Emissions", "Residents' beef — project"),
    ("R_cheese", "c_pop*p_cheese_kg_pc*p_ef_cheese/1000", "tCO2e", "Emissions", "Residents' cheese — reference"),
    ("J_cheese", "R_cheese*(1-p_cheese_red)", "tCO2e", "Emissions", "Residents' cheese — project"),
    # totals
    ("R_A", "R_elec+R_heat+R_cook+R_mob+R_farm+R_ent+R_man+R_compute", "tCO2e", "Totals", "Boundary A territorial — reference"),
    ("J_A", "J_elec+J_heat_dh+J_heat_off+J_cook+J_mob+J_farm+J_ent+J_man+J_slurry_transport+J_compute", "tCO2e", "Totals", "Boundary A territorial — project"),
    ("R_B", "R_dry+R_haul+R_feed+R_veg+R_sea+R_bread+R_beef+R_cheese", "tCO2e", "Totals", "Boundary B value chain — reference"),
    ("J_B", "J_dry+J_dry_other+J_haul+J_feed+J_veg+J_sea+J_bread+J_beef+J_cheese", "tCO2e", "Totals", "Boundary B value chain — project"),
    ("R_AB", "R_A+R_B", "tCO2e", "Totals", "A+B — reference"),
    ("J_AB", "J_A+J_B", "tCO2e", "Totals", "A+B — project"),
    ("red_A", "1-J_A/R_A", "fraction", "Totals", "Reduction, territorial"),
    ("red_B", "1-J_B/R_B", "fraction", "Totals", "Reduction, value chain"),
    ("red_AB", "1-J_AB/R_AB", "fraction", "Totals", "Reduction, A+B"),
    ("R_A_ex_compute", "R_A-R_compute", "tCO2e", "Totals", "Territorial excluding compute — reference"),
    ("J_A_ex_compute", "J_A-J_compute", "tCO2e", "Totals", "Territorial excluding compute — project"),
    ("red_A_ex_compute", "1-J_A_ex_compute/R_A_ex_compute", "fraction", "Totals", "Reduction, territorial excluding compute"),
    ("pc_R_A", "R_A_ex_compute/c_pop", "tCO2e/person", "Totals", "Per resident, territorial excl. compute — reference"),
    ("pc_J_A", "J_A_ex_compute/c_pop", "tCO2e/person", "Totals", "Per resident, territorial excl. compute — project"),
    # attribution of the A+B reduction
    ("c_ref_heat_per_gwh", "R_heat/c_heat_useful_gwh", "tCO2e/GWh useful", "Attribution", "Reference emissions per GWh of useful heat"),
    ("att_heatdisp", "c_ref_heat_per_gwh*c_dh_useful_gwh-J_heat_dh+(R_dry-J_dry)-J_dry_other", "tCO2e", "Attribution", "Recovered heat displacing fossil heat (district heating, alfalfa dehydration)"),
    ("att_food", "(R_veg-J_veg)+(R_sea-J_sea)+(R_bread-J_bread)", "tCO2e", "Attribution", "Food substitution by local production supplied with recovered heat (incl. its electricity)"),
    ("att_compute", "R_compute-J_compute", "tCO2e", "Attribution", "Compute architecture, direct (network electricity)"),
    ("att_elec", "R_elec-J_elec", "tCO2e", "Attribution", "Household electricity procurement"),
    ("att_prog", "(R_AB-J_AB)-att_heatdisp-att_food-att_compute-att_elec", "tCO2e", "Attribution", "Programme financed by compute revenue (vehicles, biogas, renewable fuels, livestock, feed, haulage, diets, off-network heat)"),
    ("att_heatdisp_share", "att_heatdisp/(R_AB-J_AB)", "fraction", "Attribution", "Heat displacement share of the A+B reduction"),
    ("att_food_share", "att_food/(R_AB-J_AB)", "fraction", "Attribution", "Food substitution share"),
    ("att_prog_share", "att_prog/(R_AB-J_AB)", "fraction", "Attribution", "Programme share"),
    ("c_heatdisp_kg_mwh_it", "att_heatdisp/c_it_gwh", "kgCO2e/MWh IT", "Attribution", "Fossil heat displaced per MWh of IT energy"),
    ("c_heatdisp_vs_compute", "att_heatdisp/J_compute", "ratio", "Attribution", "Heat displaced ÷ compute's own operational emissions"),
]

SECTORS = [  # (label, reference, project(s), boundary, attribution class)
    ("Household electricity", "R_elec", ["J_elec"], "A", "Electricity procurement"),
    ("Space heating", "R_heat", ["J_heat_dh", "J_heat_off"], "A", "Heat displacement (network) / programme (off-network)"),
    ("Cooking", "R_cook", ["J_cook"], "A", "Programme"),
    ("Private mobility", "R_mob", ["J_mob"], "A", "Programme"),
    ("Farm machinery", "R_farm", ["J_farm"], "A", "Programme"),
    ("Enteric methane", "R_ent", ["J_ent"], "A", "Programme"),
    ("Manure management", "R_man", ["J_man", "J_slurry_transport"], "A", "Programme"),
    ("Compute", "R_compute", ["J_compute"], "A", "Compute architecture"),
    ("Alfalfa dehydration", "R_dry", ["J_dry"], "B", "Heat displacement"),
    ("Other drying line", None, ["J_dry_other"], "B", "Heat displacement"),
    ("Alfalfa haulage", "R_haul", ["J_haul"], "B", "Programme"),
    ("Protein feed", "R_feed", ["J_feed"], "B", "Programme"),
    ("Vegetables", "R_veg", ["J_veg"], "B", "Food substitution"),
    ("Seafood", "R_sea", ["J_sea"], "B", "Food substitution"),
    ("Bread", "R_bread", ["J_bread"], "B", "Food substitution"),
    ("Residents' beef", "R_beef", ["J_beef"], "B", "Programme"),
    ("Residents' cheese", "R_cheese", ["J_cheese"], "B", "Programme"),
]


def _node_sum(col):
    i = {"pop": 1, "mw": 2, "area": 3}[col]
    return sum(n[i] for n in NODES)


def evaluate(overrides: dict | None = None) -> dict:
    ns = {name: val for name, val, *_ in P}
    if overrides:
        for k, v in overrides.items():
            assert k in ns, k
            ns[k] = v
    ns.update(MIN=min, MAX=max, ROUND=lambda x, d: round(x, int(d)))
    for name, expr, *_ in C:
        if expr.startswith("NODE_SUM("):
            ns[name] = _node_sum(expr[9:-1])
        else:
            ns[name] = eval(expr, {"__builtins__": {}}, ns)
    return {k: v for k, v in ns.items() if not callable(v)}


def sector_table(v):
    rows = []
    for label, r, js, b, att in SECTORS:
        ref = v[r] if r else 0.0
        proj = sum(v[j] for j in js)
        rows.append(dict(sector=label, boundary=b, attribution=att, reference_t=ref, project_t=proj,
                         reduction_t=ref - proj, reduction_pct=(1 - proj / ref) if ref else None))
    return rows


SENS = [  # (label, parameter, low, high)
    ("Reference heating mix: all natural gas ↔ all heating oil", "HEATMIX", "ng", "oil"),
    ("Livestock numbers ×0.5 ↔ ×1.5", "LIVESTOCK", 0.5, 1.5),
    ("Enteric-methane additive efficacy 0% ↔ 80%", "p_additive_eff", 0.00, 0.80),
    ("Pig slurry routed to digester 30% ↔ 100%", "p_slurry_collect", 0.30, 1.00),
    ("Digester methane avoidance 80% ↔ 95%", "p_digest_avoid", 0.80, 0.95),
    ("Biomethane-chain methane leakage 1% ↔ 6%", "p_leak", 0.01, 0.06),
    ("Renewable liquid fuel 40 ↔ 10 gCO2e/MJ", "p_ef_hvo", 0.144, 0.036),
    ("Seafood reference 5 ↔ 20 kgCO2e/kg", "p_ef_sea_ref", 5.0, 20.0),
    ("Glasshouse yield 30 ↔ 60 kg/m²", "p_yield_kg_m2", 30, 60),
    ("Useful heat per household 9,000 ↔ 18,050 kWh", "p_heat_hh", 9000, 18050),
    ("Reference dehydrator fuel 3.5 ↔ 4.5 MJ/kg water", "p_dryer_mj_kg", 3.5, 4.5),
    ("Alfalfa reference: sun-cured (no drying credit) ↔ gas dehydration", "ALFREF", "sun", "gas"),
    ("Mega-campus PUE 1.10 ↔ 1.45", "p_pue_campus", 1.10, 1.45),
    ("Network electricity 3% ↔ 0.5% of IT", "p_net_frac", 0.03, 0.005),
    ("Renewable lifecycle factor 0.04 ↔ 0.01", "RENEW", 0.04, 0.01),
]


def _apply(key, val):
    if key == "HEATMIX":
        return dict(p_mix_oil=1.0 if val == "oil" else 0.0, p_mix_lpg=0.0, p_mix_ng=1.0 if val == "ng" else 0.0, p_mix_bio=0.0)
    if key == "LIVESTOCK":
        b = {k: v for k, v, *_ in P}
        return {k: b[k] * val for k in ("p_cattle_comarca", "p_sheep_comarca", "p_pigs_comarca", "p_goats_comarca")}
    if key == "ALFREF":
        return dict(p_dryer_mj_kg=0.0) if val == "sun" else {}
    if key == "RENEW":
        return dict(p_ef_own=val, p_ef_ppa=val)
    return {key: val}


def sensitivity():
    base = evaluate()
    out = []
    for label, key, lo, hi in SENS:
        vl, vh = evaluate(_apply(key, lo)), evaluate(_apply(key, hi))
        out.append(dict(variable=label, low_red_AB=vl["red_AB"], base_red_AB=base["red_AB"], high_red_AB=vh["red_AB"],
                        low_saving_t=vl["R_AB"] - vl["J_AB"], base_saving_t=base["R_AB"] - base["J_AB"], high_saving_t=vh["R_AB"] - vh["J_AB"]))
    return out


def enteric_additive_scenarios():
    out=[]
    for label, eff in [("Central: no enteric-additive credit",0.0),("3-NOP screening case: 30% efficacy on 70% of cattle-days",0.30),("Asparagopsis upper screening case: 80% efficacy",0.80)]:
        vv=evaluate({"p_additive_eff":eff})
        out.append(dict(case=label, efficacy=eff, avoided_CH4_t=vv["c_additive_ch4_t"], integrated_reduction=vv["red_AB"]))
    return out


def scenario_bounds():
    """Joint deterministic scenario bounds. These are stress tests, not confidence intervals."""
    base = evaluate()
    # For each one-at-a-time sensitivity, choose the setting that lowers or raises the integrated-programme reduction.
    unfav = {}
    fav = {}
    for label, key, lo, hi in SENS:
        if key == "ALFREF":
            continue
        vl, vh = evaluate(_apply(key, lo)), evaluate(_apply(key, hi))
        unfav.update(_apply(key, lo if vl["red_AB"] <= vh["red_AB"] else hi))
        fav.update(_apply(key, lo if vl["red_AB"] >= vh["red_AB"] else hi))
    vu = evaluate(unfav)
    vus = evaluate({**unfav, **_apply("ALFREF", "sun")})
    vf = evaluate(fav)
    return [
        dict(case="Central", reduction=base["red_AB"], saving_t=base["R_AB"]-base["J_AB"], heatdisp_kg_mwh_it=base["c_heatdisp_kg_mwh_it"]),
        dict(case="Joint unfavourable settings; gas-dehydration reference retained", reduction=vu["red_AB"], saving_t=vu["R_AB"]-vu["J_AB"], heatdisp_kg_mwh_it=vu["c_heatdisp_kg_mwh_it"]),
        dict(case="Joint unfavourable settings plus sun-cured alfalfa reference", reduction=vus["red_AB"], saving_t=vus["R_AB"]-vus["J_AB"], heatdisp_kg_mwh_it=vus["c_heatdisp_kg_mwh_it"]),
        dict(case="Joint favourable settings; gas-dehydration reference retained", reduction=vf["red_AB"], saving_t=vf["R_AB"]-vf["J_AB"], heatdisp_kg_mwh_it=vf["c_heatdisp_kg_mwh_it"]),
    ]


def heat_metric_sensitivity():
    """Sensitivity of the distribution-specific policy metric: fossil-heat displacement per MWh IT."""
    tests = [
        ("Central", {}),
        ("Useful household heat 9,000 kWh yr-1", {"p_heat_hh": 9000}),
        ("Reference heating all natural gas", _apply("HEATMIX", "ng")),
        ("Reference heating all heating oil", _apply("HEATMIX", "oil")),
        ("Reference dehydrator 3.5 MJ kg-1 water", {"p_dryer_mj_kg": 3.5}),
        ("Reference dehydrator 4.5 MJ kg-1 water", {"p_dryer_mj_kg": 4.5}),
        ("Alfalfa reference sun-cured", _apply("ALFREF", "sun")),
    ]
    out=[]
    for label, overrides in tests:
        vv=evaluate(overrides)
        out.append(dict(case=label, heat_displacement_t=vv["att_heatdisp"], kgCO2e_per_MWh_IT=vv["c_heatdisp_kg_mwh_it"], integrated_reduction=vv["red_AB"]))
    return out


def accounting_variants():
    """Electricity-accounting variants and unmatched compute references (for transparency, not the headline)."""
    v = evaluate()
    rows = [dict(case="Integrated programme screen: market-based, campus with the same procurement and PUE", R_AB=v["R_AB"], J_AB=v["J_AB"], reduction=v["red_AB"])]
    # location-based: every project kWh at the project's location-based intensity; household reference at grid LB;
    # campus reference supplied by the same own generation first (its own own-generation share), residual at grid LB
    k = v["c_ef_proj_lb"] / v["c_ef_proj_mb"]
    elec_J = v["c_elec_total_gwh"] * v["c_ef_proj_mb"] * 1000
    J_lb = v["J_AB"] + (k - 1) * elec_J
    campus = v["c_it_gwh"] * v["p_pue_campus"]
    own = min(v["c_own_gen_gwh"], campus)
    Rc_lb = (own * v["p_ef_own"] + (campus - own) * v["p_ef_grid_lb"]) * 1000
    R_lb = v["R_AB"] - v["R_elec"] + v["c_hh_elec_gwh"] * v["p_ef_grid_lb"] * 1000 - v["R_compute"] + Rc_lb
    rows.append(dict(case="Location-based, campus with the same own generation and PUE", R_AB=R_lb, J_AB=J_lb, reduction=1 - J_lb / R_lb))
    food_R = v["R_veg"] + v["R_sea"] + v["R_bread"]; food_J = v["J_veg"] + v["J_sea"] + v["J_bread"]
    rows.append(dict(case="Market-based, excluding food substitution", R_AB=v["R_AB"] - food_R, J_AB=v["J_AB"] - food_J, reduction=1 - (v["J_AB"] - food_J) / (v["R_AB"] - food_R)))
    for label, ef, pue in [("Unmatched: campus on the residual grid mix, PUE 1.15", v["p_ef_grid_mb"], v["p_pue_campus"]),
                           ("Unmatched: campus on the residual grid mix, PUE 1.45", v["p_ef_grid_mb"], 1.45)]:
        R = v["R_AB"] - v["R_compute"] + v["c_it_gwh"] * pue * ef * 1000
        rows.append(dict(case=label, R_AB=R, J_AB=v["J_AB"], reduction=1 - v["J_AB"] / R))
    return rows


def fibre_screen(route_factor=1.25, us_km=5.0):
    def hav(a, b):
        r = 6371.0088
        p1, p2 = math.radians(a[0]), math.radians(b[0]); dp = p2 - p1; dl = math.radians(b[1] - a[1])
        h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        return 2 * r * math.asin(math.sqrt(h))
    rows = []
    for a, b in zip(NODES[:-1], NODES[1:]):
        d = hav((a[4], a[5]), (b[4], b[5]))
        rows.append(dict(**{"from": a[0], "to": b[0]}, straight_km=d, route_km=d * route_factor, one_way_us=d * route_factor * us_km))
    return rows


def write_outputs():
    os.makedirs(OUTDIR, exist_ok=True)
    v = evaluate()

    def dump(fn, rows):
        with open(os.path.join(OUTDIR, fn), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

    dump("parameters.csv", [dict(name=n, value=val, unit=u, group=g, source=s) for n, val, u, g, s in P])
    dump("calculations.csv", [dict(name=n, value=v[n], unit=u, sheet=sh, description=d, expression=e) for n, e, u, sh, d in C])
    dump("sectors.csv", sector_table(v))
    dump("sensitivity.csv", sensitivity())
    dump("enteric_additive_scenarios.csv", enteric_additive_scenarios())
    dump("scenario_bounds.csv", scenario_bounds())
    dump("heat_metric_sensitivity.csv", heat_metric_sensitivity())
    dump("accounting_variants.csv", accounting_variants())
    dump("nodes.csv", [dict(node=n[0], residents=n[1], it_MW=n[2], area_km2=n[3], lat=n[4], lon=n[5], zone=n[6],
                            it_GWh=n[2] * 8.76, recoverable_heat_GWh=n[2] * 8.76 * v["p_heat_recovery"]) for n in NODES])
    dump("fibre_screen.csv", fibre_screen())
    # Transparent biogas/manure balance used to audit the central facility assumption.
    energy_ref = v["R_elec"] + v["R_heat"] + v["R_cook"] + v["R_mob"] + v["R_farm"]
    energy_proj = v["J_elec"] + v["J_heat_dh"] + v["J_heat_off"] + v["J_cook"] + v["J_mob"] + v["J_farm"]
    managed_ref_ch4_t = (v["c_pigs"]*v["p_man_pig"]*v["p_slurry_collect"] + v["c_cattle"]*v["p_man_cattle"]*v["p_cattle_manure_collect"])/1000
    gross_biogas_ch4_t = v["c_biogas_ch4_m3"]*v["p_ch4_kg_m3"]/1000
    managed_resid_ch4_t = managed_ref_ch4_t*(1-v["p_digest_avoid"]) + v["c_leak_ch4_t"]
    dump("biogas_balance.csv", [
        dict(metric="Pig slurry routed to digester", value=v["p_slurry_collect"], unit="fraction"),
        dict(metric="Cattle manure routed (housed/collectable share)", value=v["p_cattle_manure_collect"], unit="fraction of total cattle manure"),
        dict(metric="Managed-manure storage CH4 avoided", value=v["p_digest_avoid"], unit="fraction"),
        dict(metric="Biomethane-chain methane leakage", value=v["p_leak"], unit="fraction of gross biogas CH4"),
        dict(metric="Managed-manure + biomethane-chain residual methane intensity", value=managed_resid_ch4_t/gross_biogas_ch4_t, unit="fraction of gross biogas CH4"),
        dict(metric="Wet manure transported", value=v["c_slurry_truck_t"], unit="t/yr"),
        dict(metric="Average one-way manure haul", value=v["p_slurry_haul_oneway_km"], unit="km"),
        dict(metric="Slurry/manure transport emissions", value=v["c_slurry_truck_tco2"], unit="tCO2e/yr"),
        dict(metric="Reference manure methane", value=v["R_man"], unit="tCO2e/yr"),
        dict(metric="Project manure methane", value=v["J_man"], unit="tCO2e/yr"),
        dict(metric="Manure methane reduction", value=1-v["J_man"]/v["R_man"], unit="fraction"),
        dict(metric="Biomethane produced", value=v["c_biomethane_gwh"], unit="GWh/yr"),
        dict(metric="Biomethane to cooking", value=v["c_bio_cook_gwh"], unit="GWh/yr"),
        dict(metric="Biomethane to farm machinery", value=v["c_bio_farm_gwh"], unit="GWh/yr"),
        dict(metric="Biomethane to off-network heating", value=v["c_bio_heat_gwh"], unit="GWh/yr"),
        dict(metric="Renewable heating oil/diesel to off-network heating", value=v["c_heat_hvo_gwh"], unit="GWh/yr"),
        dict(metric="Renewable diesel to farm machinery", value=v["c_farm_hvo_gwh"], unit="GWh/yr"),
        dict(metric="Predefined five-sector directly addressable energy-service reduction", value=1-energy_proj/energy_ref, unit="fraction"),
    ])
    return v


if __name__ == "__main__":
    v = write_outputs()
    keys = ["c_pop", "c_it_mw", "c_hh", "c_dh_hh", "c_veh", "c_cattle", "c_sheep", "c_pigs", "c_cult_ha",
            "c_man_ch4_t", "c_digest_ch4_t", "c_leak_ch4_t", "c_slurry_truck_tco2", "c_biomethane_gwh",
            "c_bio_cook_gwh", "c_bio_farm_gwh", "c_bio_heat_gwh", "c_heat_hvo_gwh", "c_bio_surplus_gwh", "c_elec_total_gwh", "c_own_gen_gwh", "c_ppa_gwh",
            "c_ef_proj_mb", "c_heat_used_gwh", "c_heat_rejected_gwh", "c_erf", "R_A", "J_A", "red_A", "R_B", "J_B", "red_B",
            "R_AB", "J_AB", "red_AB", "red_A_ex_compute", "pc_R_A", "pc_J_A", "att_heatdisp", "att_food", "att_prog", "att_elec", "att_compute", "att_heatdisp_share", "att_food_share", "att_prog_share", "c_heatdisp_kg_mwh_it", "c_heatdisp_vs_compute"]
    for k in keys:
        print(f"{k:24s} {v[k]:,.4f}")
    print()
    for r in sector_table(v):
        print(f"{r['sector']:22s} {r['boundary']} {r['reference_t']:>11,.0f} {r['project_t']:>10,.0f} {r['reduction_t']:>11,.0f}")
