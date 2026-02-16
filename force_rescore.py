from src.feedback.rescoring_engine import RescoringEngine

def force_rescore():
    print("Forcing full re-score of all companies to synchronize labels...")
    engine = RescoringEngine()
    engine.rescore_all()
    print("Re-score complete.")

if __name__ == "__main__":
    force_rescore()
