from app_brain.schema_parser import Endpoint

def score_endpoint(request: str, endpoint: Endpoint) -> float:
    request_words = set(request.lower().split())
    text = f"{endpoint.summary} {endpoint.path}".lower()
    text_words = set(text.replace("/", " ").replace("{", " ").replace("}", " ").split())
    overlap = request_words & text_words
    return len(overlap) / (len(text_words) or 1)

def get_candidates(request: str, endpoints: list[Endpoint], top_k: int = 3) -> list[Endpoint]:
    scored = [(score_endpoint(request, e), e) for e in endpoints]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [e for score, e in scored[:top_k] if score > 0]

if __name__ == "__main__":
    from app_brain.schema_parser import load_endpoints
    endpoints = load_endpoints("openapi_live.json", "stubs/risk_tiers.json")

    test_request = "cancel John's subscription"
    candidates = get_candidates(test_request, endpoints)
    print(f"Request: {test_request}")
    for c in candidates:
        print(f"  {c.method} {c.path} — {c.summary}")