import math

def calculate_dcf_ev(fcf_0: float, g: float, wacc: float, g_term: float, years: int = 10) -> float:
    if fcf_0 <= 0 or wacc <= g_term:
        return 0.0
    
    pv_explicit = 0.0
    current_fcf = fcf_0
    
    for t in range(1, years + 1):
        current_fcf *= (1.0 + g)
        discount_factor = math.pow(1.0 + wacc, t)
        pv_explicit += current_fcf / discount_factor
        
    fcf_terminal = current_fcf * (1.0 + g_term)
    terminal_value = fcf_terminal / (wacc - g_term)
    pv_terminal = terminal_value / math.pow(1.0 + wacc, years)
    
    return pv_explicit + pv_terminal

def solve_implied_fcf_cagr(
    ev: float,
    fcf_0: float,
    wacc: float = 0.115,
    g_term: float = 0.05,
    years: int = 10
) -> float:
    if fcf_0 <= 0 or ev <= 0:
        return 0.0
    
    # Binary search for g between -20% and +60%
    low = -0.20
    high = 0.80
    
    for _ in range(60):
        mid = (low + high) / 2.0
        val = calculate_dcf_ev(fcf_0, mid, wacc, g_term, years)
        if val < ev:
            low = mid
        else:
            high = mid
            
    return mid * 100.0

def run_reverse_dcf(
    cmp: float,
    mcap_cr: float,
    fcf_0: float,
    net_debt: float = 0.0,
    wacc: float = 0.115,
    g_term: float = 0.05
):
    ev = mcap_cr + net_debt
    base_fcf = max(1.0, fcf_0)
    
    implied_cagr = solve_implied_fcf_cagr(ev, base_fcf, wacc, g_term)
    
    if implied_cagr < 15.0:
        assessment = "REALISTIC / MODEST (<15%)"
        color = "green"
    elif implied_cagr <= 25.0:
        assessment = "AGGRESSIVE (15% - 25%)"
        color = "orange"
    else:
        assessment = "HEROIC / PRICED TO PERFECTION (>25%)"
        color = "red"

    # Sensitivity Matrix across WACCs and Terminal Growths
    wacc_list = [0.10, 0.115, 0.13]
    g_term_list = [0.04, 0.05, 0.06]
    
    matrix = {}
    for w in wacc_list:
        w_key = f"{int(w*100)}%" if w != 0.115 else "11.5%"
        matrix[w_key] = {}
        for gt in g_term_list:
            gt_key = f"{int(gt*100)}%"
            matrix[w_key][gt_key] = round(solve_implied_fcf_cagr(ev, base_fcf, w, gt), 1)

    return {
        "ev": round(ev, 1),
        "fcf_0": round(base_fcf, 1),
        "wacc_pct": round(wacc * 100, 1),
        "g_term_pct": round(g_term * 100, 1),
        "implied_cagr": round(implied_cagr, 1),
        "assessment": assessment,
        "color": color,
        "sensitivity_matrix": matrix
    }
