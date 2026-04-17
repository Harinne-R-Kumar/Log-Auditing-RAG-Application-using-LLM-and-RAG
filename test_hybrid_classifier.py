#!/usr/bin/env python3
print("=" * 50)
print("Testing Hybrid Classifier...")
print("=" * 50)

try:
    from services.hybrid_classifier import HybridClassifier
    print("Hybrid classifier imported successfully")
    
    # Test classification
    classifier = HybridClassifier()
    print(f"Classifier initialized successfully")
    print(f"Using PyTorch: {classifier.use_pytorch}")
    
    test_logs = [
        {"message": "database connection failed", "severity": ""},
        {"message": "user login successful", "severity": ""},
        {"message": "critical memory error", "severity": ""},
        {"message": "warning: high latency detected", "severity": ""}
    ]
    
    results = classifier.classify_logs(test_logs)
    print("Classification results:")
    for log in results:
        print(f"  '{log['message']}' -> {log['severity']} (source: {log['severity_source']})")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print("=" * 50)
input("Press Enter to exit...")
