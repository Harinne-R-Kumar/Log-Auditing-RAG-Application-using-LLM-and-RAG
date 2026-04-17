#!/usr/bin/env python3
print("=" * 50)
print("Testing PyTorch Classifier...")
print("=" * 50)

try:
    import torch
    print("PyTorch version:", torch.__version__)
    print("CUDA available:", torch.cuda.is_available())
except ImportError:
    print("PyTorch not installed - will use fallback")

try:
    from services.pytorch_classifier import PyTorchHybridClassifier
    print("PyTorch classifier imported successfully")
    
    # Test classification
    classifier = PyTorchHybridClassifier()
    print("Classifier initialized successfully")
    
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
