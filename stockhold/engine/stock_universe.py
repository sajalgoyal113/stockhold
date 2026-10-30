"""
stock_universe.py - Comprehensive Indexed Universe of Indian Listed Equities (NSE / BSE)

Provides indexed stock symbols, names, and industry sectors for instant search autocomplete,
along with real-time fallback to Screener search API for all 4,000+ listed Indian equities.
"""

import re
import requests

INDEXED_INDIAN_STOCKS = [
    # Top Compounders & Emerging Leaders
    {"ticker": "COFORGE", "name": "Coforge Ltd", "sector": "Enterprise IT & Solutions"},
    {"ticker": "KPITTECH", "name": "KPIT Technologies Ltd", "sector": "Automotive Software & Mobility"},
    {"ticker": "TRENT", "name": "Trent Ltd", "sector": "Retail (Zudio & Westside)"},
    {"ticker": "ETERNAL", "name": "Zomato / Eternal Ltd", "sector": "Quick-Commerce & Food Delivery"},
    {"ticker": "DIXON", "name": "Dixon Technologies (India) Ltd", "sector": "Electronic Manufacturing Services (EMS)"},
    {"ticker": "KAYNES", "name": "Kaynes Technology India Ltd", "sector": "Defense EMS & OSAT Semiconductor"},
    {"ticker": "ADVAIT", "name": "Advait Energy Transition Ltd", "sector": "Green Hydrogen & Power EPC"},
    {"ticker": "TECHNOE", "name": "Techno Electric & Engineering Ltd", "sector": "Data Centers & Smart Grid EPC"},
    {"ticker": "NETWEB", "name": "Netweb Technologies India Ltd", "sector": "AI Supercomputing & High-End Servers"},
    {"ticker": "CYIENTDLM", "name": "Cyient DLM Ltd", "sector": "Aerospace & Defense Electronics"},
    {"ticker": "PGEL", "name": "PG Electroplast Ltd", "sector": "Consumer Electronics & Appliances EMS"},
    {"ticker": "AMBER", "name": "Amber Enterprises India Ltd", "sector": "HVAC Components & Railway Subsystems"},
    {"ticker": "JYOTICNC", "name": "Jyoti CNC Automation Ltd", "sector": "Aerospace & High-Precision CNC Machines"},
    {"ticker": "SUZLON", "name": "Suzlon Energy Ltd", "sector": "Renewable Wind Energy & Turbines"},
    {"ticker": "POLYCAB", "name": "Polycab India Ltd", "sector": "Wires, Cables & Fast Moving Electrical Goods"},
    {"ticker": "KEI", "name": "KEI Industries Ltd", "sector": "Extra High Voltage (EHV) Power Cables"},
    {"ticker": "HAL", "name": "Hindustan Aeronautics Ltd", "sector": "Defense Aviation & Fighter Jets"},
    {"ticker": "BEL", "name": "Bharat Electronics Ltd", "sector": "Defense Radar & Electronic Warfare"},
    {"ticker": "MAZDOCK", "name": "Mazagon Dock Shipbuilders Ltd", "sector": "Defense Submarines & Naval Warships"},
    {"ticker": "COCHINSHIP", "name": "Cochin Shipyard Ltd", "sector": "Naval Aircraft Carriers & Commercial Vessels"},
    {"ticker": "DATAPATTNS", "name": "Data Patterns (India) Ltd", "sector": "Defense Avionics & Satellite Systems"},
    {"ticker": "PARAS", "name": "Paras Defence & Space Technologies", "sector": "Defense Optics & Space Mechanisms"},
    {"ticker": "SOLARINDS", "name": "Solar Industries India Ltd", "sector": "Industrial Explosives & Defense Warheads"},
    {"ticker": "MTARTECH", "name": "MTAR Technologies Ltd", "sector": "Clean Energy, Space & Nuclear Assemblies"},
    {"ticker": "TATAELXSI", "name": "Tata Elxsi Ltd", "sector": "Autonomous Driving AI & Product Engineering"},
    {"ticker": "PERSISTENT", "name": "Persistent Systems Ltd", "sector": "Cloud, Data & Digital Product Engineering"},
    {"ticker": "LTIM", "name": "LTIMindtree Ltd", "sector": "Tier-1 Enterprise IT Consulting"},
    {"ticker": "TCS", "name": "Tata Consultancy Services Ltd", "sector": "Global Enterprise IT & Cloud Solutions"},
    {"ticker": "INFY", "name": "Infosys Ltd", "sector": "Enterprise Digital Transformation"},
    {"ticker": "HCLTECH", "name": "HCL Technologies Ltd", "sector": "Digital Services & Engineering R&D"},
    {"ticker": "WIPRO", "name": "Wipro Ltd", "sector": "IT Consulting & AI Orchestration"},
    {"ticker": "TECHM", "name": "Tech Mahindra Ltd", "sector": "Telecom & Enterprise Digital Engineering"},
    {"ticker": "BSOFT", "name": "Birlasoft Ltd", "sector": "Enterprise Digital Transformation & ERP"},
    {"ticker": "SONACOMS", "name": "Sona BLW Precision Forgings Ltd", "sector": "Electric Vehicle Driveline & Differential Gears"},
    {"ticker": "UNOMINDA", "name": "Uno Minda Ltd", "sector": "Automotive Lighting, Sensors & Alloy Wheels"},
    {"ticker": "CIEINDIA", "name": "CIE Automotive India Ltd", "sector": "Forged & Cast Automotive Components"},
    {"ticker": "MOTHERSON", "name": "Samvardhana Motherson International Ltd", "sector": "Wiring Harnesses & Automotive Systems"},
    {"ticker": "BHARTIARTL", "name": "Bharti Airtel Ltd", "sector": "Telecom, Cloud Infrastructure & Data Centers"},
    {"ticker": "RELIANCE", "name": "Reliance Industries Ltd", "sector": "Retail, Telecom (Jio) & Energy Transition"},
    {"ticker": "HDFCBANK", "name": "HDFC Bank Ltd", "sector": "Private Banking & Financial Services"},
    {"ticker": "ICICIBANK", "name": "ICICI Bank Ltd", "sector": "Private Banking & Digital Lending"},
    {"ticker": "KOTAKBANK", "name": "Kotak Mahindra Bank Ltd", "sector": "Private Banking & Wealth Management"},
    {"ticker": "AXISBANK", "name": "Axis Bank Ltd", "sector": "Private Banking & Corporate Credit"},
    {"ticker": "SBIN", "name": "State Bank of India", "sector": "Public Sector Banking & National Infrastructure"},
    {"ticker": "BAJFINANCE", "name": "Bajaj Finance Ltd", "sector": "Consumer Lending, Omnichannel Retail NBFC"},
    {"ticker": "BAJAJFINSV", "name": "Bajaj Finserv Ltd", "sector": "Financial Services, Insurance & Wealth"},
    {"ticker": "CHOLAFIN", "name": "Cholamandalam Investment and Finance Co", "sector": "Vehicle Financing & MSME Credit"},
    {"ticker": "SHRIRAMFIN", "name": "Shriram Finance Ltd", "sector": "Commercial Vehicle & Rural Lending"},
    {"ticker": "MUTHOOTFIN", "name": "Muthoot Finance Ltd", "sector": "Gold-Backed Micro & Retail Financing"},
    {"ticker": "MANAPPURAM", "name": "Manappuram Finance Ltd", "sector": "Gold Lending & Microfinance"},
    {"ticker": "ANGELONE", "name": "Angel One Ltd", "sector": "Fintech Brokerage & Algorithmic Wealth"},
    {"ticker": "CDSL", "name": "Central Depository Services (India) Ltd", "sector": "Capital Markets Depository Monopolist"},
    {"ticker": "BSE", "name": "BSE Ltd", "sector": "Capital Markets Exchange & Derivative Platform"},
    {"ticker": "MCX", "name": "Multi Commodity Exchange of India Ltd", "sector": "Commodity Exchange & Options Monopoly"},
    {"ticker": "CAMS", "name": "Computer Age Management Services Ltd", "sector": "Mutual Fund Registrar & Transfer Agent"},
    {"ticker": "KFINTECH", "name": "KFin Technologies Ltd", "sector": "Global SaaS Registry & Asset Servicing"},
    {"ticker": "PAYTM", "name": "One97 Communications Ltd (Paytm)", "sector": "Digital Payments & Soundbox Infrastructure"},
    {"ticker": "POLICYBZR", "name": "PB Fintech Ltd (PolicyBazaar)", "sector": "Online Insurance & Credit Aggregator"},
    {"ticker": "NAUKRI", "name": "Info Edge (India) Ltd", "sector": "Recruitment (Naukri) & Real Estate (99acres)"},
    {"ticker": "ZOMATO", "name": "Zomato Ltd (Eternal)", "sector": "Quick-Commerce (Blinkit) & Hyperlocal Delivery"},
    {"ticker": "IXIGO", "name": "Le Travenues Technology Ltd (ixigo)", "sector": "AI-Powered Rail, Bus & Flight Travel OTA"},
    {"ticker": "EASEMYTRIP", "name": "Easy Trip Planners Ltd", "sector": "Online Travel Booking & Zero-Convenience Fee"},
    {"ticker": "MAPMYINDIA", "name": "C.E. Info Systems Ltd (MapmyIndia)", "sector": "B2B Digital Navigation Maps & Autonomous IoT"},
    {"ticker": "TATAMOTORS", "name": "Tata Motors Ltd", "sector": "EV Passenger Cars, Commercial Vehicles & JLR"},
    {"ticker": "M&M", "name": "Mahindra & Mahindra Ltd", "sector": "SUVs, Electric Vehicles & Farm Tractors"},
    {"ticker": "MARUTI", "name": "Maruti Suzuki India Ltd", "sector": "Passenger Automotive & Hybrid Systems"},
    {"ticker": "BAJAJ-AUTO", "name": "Bajaj Auto Ltd", "sector": "Two-Wheelers, Commercial 3-Wheelers & Chetak EV"},
    {"ticker": "TVSMOTOR", "name": "TVS Motor Company Ltd", "sector": "Two-Wheelers, Racing & iQube EV"},
    {"ticker": "HEROMOTOCO", "name": "Hero MotoCorp Ltd", "sector": "Commuter Motorcycles & Vida EV"},
    {"ticker": "EICHERMOT", "name": "Eicher Motors Ltd", "sector": "Royal Enfield Premium Motorcycles & Commercial Trucks"},
    {"ticker": "TITAN", "name": "Titan Company Ltd", "sector": "Tanishq Luxury Jewellery, Watches & Eyewear"},
    {"ticker": "DMART", "name": "Avenue Supermarts Ltd (DMart)", "sector": "Hypermarket Retail & Omnichannel Grocery"},
    {"ticker": "KALYANKJIL", "name": "Kalyan Jewellers India Ltd", "sector": "Pan-India Jewellery Showroom Chain"},
    {"ticker": "SENCO", "name": "Senco Gold Ltd", "sector": "Eastern India & Pan-India Jewellery Retail"},
    {"ticker": "ETHOSLTD", "name": "Ethos Ltd", "sector": "Luxury Swiss Watch Retail Chain"},
    {"ticker": "VAIBHAVGBL", "name": "Vaibhav Global Ltd", "sector": "Direct-to-Consumer TV & E-Commerce Retail"},
    {"ticker": "ASIANPAINT", "name": "Asian Paints Ltd", "sector": "Decorative Coatings & Home Decor"},
    {"ticker": "BERGEPAINT", "name": "Berger Paints India Ltd", "sector": "Decorative & Industrial Coatings"},
    {"ticker": "PIDILITIND", "name": "Pidilite Industries Ltd", "sector": "Fevicol Adhesives, Sealants & Construction Chemicals"},
    {"ticker": "ASTRAL", "name": "Astral Ltd", "sector": "CPVC Plumbing Pipes, Adhesives & Sanitaryware"},
    {"ticker": "SUPREMEIND", "name": "Supreme Industries Ltd", "sector": "Plastic Products, Piping Systems & Packaging"},
    {"ticker": "FINPIPE", "name": "Finolex Industries Ltd", "sector": "PVC Pipes & Resins"},
    {"ticker": "HINDUNILVR", "name": "Hindustan Unilever Ltd", "sector": "Fast Moving Consumer Goods (FMCG) & Personal Care"},
    {"ticker": "ITC", "name": "ITC Ltd", "sector": "FMCG, Cigarettes, Hotels & Agri-Business"},
    {"ticker": "NESTLEIND", "name": "Nestle India Ltd", "sector": "Packaged Food, Maggi & Dairy Products"},
    {"ticker": "BRITANNIA", "name": "Britannia Industries Ltd", "sector": "Biscuits, Dairy & Bakery Products"},
    {"ticker": "TATACONSUM", "name": "Tata Consumer Products Ltd", "sector": "Packaged Tea, Salt, Sampann & Ready-to-Drink"},
    {"ticker": "DABUR", "name": "Dabur India Ltd", "sector": "Ayurvedic Healthcare & Natural Consumer Products"},
    {"ticker": "MARICO", "name": "Marico Ltd", "sector": "Parachute Coconut Oil & Saffola Edible Oils"},
    {"ticker": "COLPAL", "name": "Colgate-Palmolive (India) Ltd", "sector": "Oral Care & Dental Hygiene"},
    {"ticker": "GODREJCP", "name": "Godrej Consumer Products Ltd", "sector": "Household Insecticides & Personal Care"},
    {"ticker": "VBL", "name": "Varun Beverages Ltd", "sector": "PepsiCo Bottling Franchisee across India & Africa"},
    {"ticker": "BIKAJI", "name": "Bikaji Foods International Ltd", "sector": "Ethnic Snacks, Bhujia & Packaged Sweets"},
    {"ticker": "PRATAAP", "name": "Prataap Snacks Ltd (Yellow Diamond)", "sector": "Extruded Potato Chips & Namkeen"},
    {"ticker": "GOPAL", "name": "Gopal Snacks Ltd", "sector": "Western & Regional Savory Snacks"},
    {"ticker": "LT", "name": "Larsen & Toubro Ltd", "sector": "Infrastructure Engineering, Defense & Mega-EPC"},
    {"ticker": "SIEMENS", "name": "Siemens Ltd", "sector": "Industrial Automation, Electrification & Rail Locos"},
    {"ticker": "ABB", "name": "ABB India Ltd", "sector": "Robotics, Motion & Power Grids Automation"},
    {"ticker": "THERMAX", "name": "Thermax Ltd", "sector": "Clean Air, Green Energy & Decarbonization Boilers"},
    {"ticker": "TRITURBINE", "name": "Triveni Turbine Ltd", "sector": "Industrial Steam Turbines & Waste-to-Energy"},
    {"ticker": "CUMMINSIND", "name": "Cummins India Ltd", "sector": "Diesel Engines & Backup Power Generation"},
    {"ticker": "PFC", "name": "Power Finance Corporation Ltd", "sector": "Power Sector Infrastructure Lending"},
    {"ticker": "RECLTD", "name": "REC Ltd", "sector": "Green Energy & Rural Electrification Financing"},
    {"ticker": "POWERGRID", "name": "Power Grid Corporation of India Ltd", "sector": "National Interstate Power Transmission Monopoly"},
    {"ticker": "NTPC", "name": "NTPC Ltd", "sector": "Thermal & Utility-Scale Renewable Power"},
    {"ticker": "TATAPOWER", "name": "Tata Power Company Ltd", "sector": "Integrated Utility, Solar Rooftops & EV Charging"},
    {"ticker": "JSWENERGY", "name": "JSW Energy Ltd", "sector": "Renewable Power & Energy Storage"},
    {"ticker": "ADANIGREEN", "name": "Adani Green Energy Ltd", "sector": "Utility-Scale Solar & Wind Hybrid Energy"},
    {"ticker": "ADANIPORTS", "name": "Adani Ports and Special Economic Zone Ltd", "sector": "Commercial Seaports & Logistics Corridors"},
    {"ticker": "KNRCON", "name": "KNR Constructions Ltd", "sector": "Highways, Expressways & Irrigation EPC"},
    {"ticker": "PNCINFRA", "name": "PNC Infratech Ltd", "sector": "Road EPC, Bridges & Airport Runways"},
    {"ticker": "GRINFRA", "name": "G R Infraprojects Ltd", "sector": "Roads, Rail Metros & Optical Fiber Networks"},
    {"ticker": "PRESTIGE", "name": "Prestige Estates Projects Ltd", "sector": "Premium Residential, Tech Parks & Retail Malls"},
    {"ticker": "GODREJPROP", "name": "Godrej Properties Ltd", "sector": "Pan-India Residential Real Estate Developer"},
    {"ticker": "OBEROIRLTY", "name": "Oberoi Realty Ltd", "sector": "Mumbai Luxury Residential & Integrated Enclaves"},
    {"ticker": "DLF", "name": "DLF Ltd", "sector": "Gurugram Luxury Real Estate & Commercial Offices"},
    {"ticker": "MACROTECH", "name": "Macrotech Developers Ltd (Lodha)", "sector": "Residential Enclaves & Industrial Logistics Parks"},
    {"ticker": "PHOENIXLTD", "name": "The Phoenix Mills Ltd", "sector": "Destination Retail Malls & Mixed-Use Real Estate"},
    {"ticker": "SUNPHARMA", "name": "Sun Pharmaceutical Industries Ltd", "sector": "Specialty Dermatology & Global Generics"},
    {"ticker": "CIPLA", "name": "Cipla Ltd", "sector": "Respiratory Inhalers & Domestic Formulations"},
    {"ticker": "DRREDDY", "name": "Dr. Reddy's Laboratories Ltd", "sector": "Global Generics, Biosimilars & APIs"},
    {"ticker": "DIVISLAB", "name": "Divi's Laboratories Ltd", "sector": "Custom Synthesis & Active Pharmaceutical Ingredients (API)"},
    {"ticker": "LUPIN", "name": "Lupin Ltd", "sector": "Inhalation, Injectables & Cardiovascular Formulations"},
    {"ticker": "APOLLOHOSP", "name": "Apollo Hospitals Enterprise Ltd", "sector": "Super-Specialty Hospitals, Clinics & Apollo 24/7"},
    {"ticker": "MAXHEALTH", "name": "Max Healthcare Institute Ltd", "sector": "Metropolitan Quaternary Care Hospital Network"},
    {"ticker": "FORTIS", "name": "Fortis Healthcare Ltd", "sector": "Pan-India Hospitals & SRL Diagnostics"},
    {"ticker": "MEDANTA", "name": "Global Health Ltd (Medanta)", "sector": "North India Quaternary Care Hospitals"},
    {"ticker": "NARAYANA", "name": "Narayana Hrudayalaya Ltd", "sector": "Affordable Cardiac & Multispecialty Hospitals"},
    {"ticker": "RAINBOW", "name": "Rainbow Children's Medicare Ltd", "sector": "Pediatric & Perinatal Super-Specialty Healthcare"},
    {"ticker": "KIMS", "name": "Krishna Institute of Medical Sciences Ltd", "sector": "Tier-2/3 Affordable Multispecialty Healthcare"},
    {"ticker": "LALPATHLAB", "name": "Dr. Lal PathLabs Ltd", "sector": "Diagnostic Pathology Laboratories & Collection Centers"},
    {"ticker": "METROPOLIS", "name": "Metropolis Healthcare Ltd", "sector": "Clinical Pathology & Diagnostic Testing Network"},
    {"ticker": "DEEPAKNTR", "name": "Deepak Nitrite Ltd", "sector": "Sodium Nitrite, Phenol & Specialty Intermediates"},
    {"ticker": "SRF", "name": "SRF Ltd", "sector": "Fluorochemicals, Specialty Chemicals & Packaging Films"},
    {"ticker": "NAVINFLUOR", "name": "Navin Fluorine International Ltd", "sector": "Specialty Fluorination & High-Purity Agro Intermediates"},
    {"ticker": "GUJFLUORO", "name": "Gujarat Fluorochemicals Ltd", "sector": "Fluoropolymers, Battery Chemicals & Industrial Gases"},
    {"ticker": "PIIND", "name": "PI Industries Ltd", "sector": "Custom Synthesis (CSM) & Agrochemical Innovation"},
    {"ticker": "AARTIIND", "name": "Aarti Industries Ltd", "sector": "Benzene Derivatives & Specialty Intermediates"},
    {"ticker": "FINEORG", "name": "Fine Organic Industries Ltd", "sector": "Oleochemical Green Additives for Plastics & Food"},
    {"ticker": "CLEAN", "name": "Clean Science and Technology Ltd", "sector": "Eco-Friendly Catalytic Performance Chemicals"},
    {"ticker": "TATASTEEL", "name": "Tata Steel Ltd", "sector": "Integrated Flat & Long Steel Manufacturing"},
    {"ticker": "JSWSTEEL", "name": "JSW Steel Ltd", "sector": "Flat Steel, Coils & Infrastructure Rebars"},
    {"ticker": "HINDALCO", "name": "Hindalco Industries Ltd", "sector": "Aluminium Smelting & Novelis Beverage Cans"},
    {"ticker": "JINDALSTEL", "name": "Jindal Steel & Power Ltd", "sector": "Steel Plates, Rail Tracks & Power Generation"},
    {"ticker": "VEDL", "name": "Vedanta Ltd", "sector": "Diversified Natural Resources & Metals"},
    {"ticker": "COALINDIA", "name": "Coal India Ltd", "sector": "Thermal Coal Mining & Energy Security Monopoly"},
    {"ticker": "ULTRACEMCO", "name": "UltraTech Cement Ltd", "sector": "Grey Cement, Ready-Mix Concrete & Building Materials"},
    {"ticker": "AMBUJACEM", "name": "Ambuja Cements Ltd", "sector": "Cement Manufacturing & Logistics"},
    {"ticker": "SHREECEM", "name": "Shree Cement Ltd", "sector": "Cost-Efficient Green Cement Producer"},
    {"ticker": "DALBHARAT", "name": "Dalmia Bharat Ltd", "sector": "Eastern & Southern India Cement Expansion"},
    {"ticker": "INDIGO", "name": "InterGlobe Aviation Ltd (IndiGo)", "sector": "Commercial Aviation & Fleet Domination Monopoly"},
    {"ticker": "IRCTC", "name": "Indian Railway Catering & Tourism Corp", "sector": "Rail Ticketing, Catering & Rail Neer Monopoly"},
    {"ticker": "CONCOR", "name": "Container Corporation of India Ltd", "sector": "Inland Rail Container Freight & Multimodal Logistics"},
    {"ticker": "DELHIVERY", "name": "Delhivery Ltd", "sector": "Automated Parcel Logistics & Express Freight"},
    {"ticker": "BLUEDART", "name": "Blue Dart Express Ltd", "sector": "Air Express Courier & Document Delivery"},
    {"ticker": "TCIEXP", "name": "TCI Express Ltd", "sector": "Surface & Air Express Cargo Logistics"},
    {"ticker": "ALLCARGO", "name": "Allcargo Logistics Ltd", "sector": "Global Less-than-Container Load (LCL) Freight"},
    # Portfolio & Special Situation High-Growth Universe
    {"ticker": "SYRMA", "name": "Syrma SGS Technology Ltd", "sector": "EMS, High-Precision PCBAs & RFID Solutions"},
    {"ticker": "EMMVEE", "name": "Emmvee Photovoltaic Power Ltd", "sector": "Solar PV Modules & TOPCon Solar Cells"},
    {"ticker": "CLEANMAX", "name": "Clean Max Enviro Energy Solutions Ltd", "sector": "C&I Renewable Energy Independent Power Producer"},
    {"ticker": "AMARAJABAT", "name": "Amara Raja Energy & Mobility Ltd", "sector": "Industrial & EV Batteries, BESS & Gigafactory"},
    {"ticker": "YATHARTH", "name": "Yatharth Hospital & Trauma Care Services Ltd", "sector": "Regional Multi-Specialty Tertiary Healthcare"},
    {"ticker": "SJS", "name": "SJS Enterprises Ltd", "sector": "Automotive Aesthetics & In-Mould Electronics"},
    {"ticker": "IONEXCHANG", "name": "Ion Exchange (India) Ltd", "sector": "Industrial Water Treatment, Resins & Effluent Plants"},
    {"ticker": "AHLUCONT", "name": "Ahluwalia Contracts (India) Ltd", "sector": "Institutional Civil Engineering & Hospital EPC"},
    {"ticker": "SAMHI", "name": "SAMHI Hotels Ltd", "sector": "Branded Hospitality Ownership & Asset Management"},
    {"ticker": "EIEL", "name": "Enviro Infra Engineers Ltd", "sector": "Wastewater Treatment (STP/CETP) & Urban Water Supply"},
    {"ticker": "STALLION", "name": "Stallion India Fluorochemicals Ltd", "sector": "Specialty Fluorochemicals & Refrigerant Gases"},
    {"ticker": "UTKARSHBNK", "name": "Utkarsh Small Finance Bank Ltd", "sector": "Microfinance & Small Finance Banking"},
    {"ticker": "ASSOCHALC", "name": "Associated Alcohols & Breweries Ltd", "sector": "Distilleries, Grain ENA & Proprietary IMFL"},
    {"ticker": "ECORECO", "name": "Eco Recycling Ltd", "sector": "E-Waste Recycling & Precious Metal Recovery"},
    {"ticker": "VPRPL", "name": "Vishnu Prakash R Punglia Ltd", "sector": "Water Supply EPC & Railway Infrastructure"},
    {"ticker": "ASALCBR", "name": "Associated Alcohols & Breweries Ltd", "sector": "Distilleries & IMFL Manufacturing"},
]


_INDEXED_STOCK_OPTIONS_CACHE = None

def get_indexed_stock_options() -> list[str]:
    """Returns formatted display strings for searchable selectbox / autocomplete."""
    global _INDEXED_STOCK_OPTIONS_CACHE
    if _INDEXED_STOCK_OPTIONS_CACHE is None:
        _INDEXED_STOCK_OPTIONS_CACHE = [f"{s['ticker']} — {s['name']} ({s['sector']})" for s in INDEXED_INDIAN_STOCKS]
    return _INDEXED_STOCK_OPTIONS_CACHE


def extract_ticker_from_string(selection: str) -> str:
    """Extracts ticker symbol from either a direct symbol or a 'TICKER — Name' string."""
    if not selection:
        return ""
    clean = selection.strip().upper()
    if "—" in clean:
        return clean.split("—")[0].strip()
    if "-" in clean:
        return clean.split("-")[0].strip()
    if " " in clean:
        return clean.split()[0].strip()
    return clean


def search_online_screener(query: str, limit: int = 8) -> list[dict]:
    """
    Queries Screener search API dynamically for any of the 4,000+ Indian listed equities.
    Returns list of dicts with ticker, name, and url.
    """
    clean_q = query.strip()
    if not clean_q or len(clean_q) < 2:
        return []
    try:
        url = f"https://www.screener.in/api/company/search/?q={requests.utils.quote(clean_q)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            results = []
            for item in data[:limit]:
                m = re.search(r"/company/([^/]+)/", item.get("url", ""))
                if m:
                    t = m.group(1).upper()
                    results.append({
                        "ticker": t,
                        "name": item.get("name", t),
                        "display": f"{t} — {item.get('name', t)}"
                    })
            return results
    except Exception:
        pass
    return []
