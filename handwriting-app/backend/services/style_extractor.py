# HandwritingAI — style_extractor.py


def extract_style(image_paths: list[str]) -> dict:
    from uuid import uuid4

    # Style is now extracted at generation time using MobileNet
    # inside DiffusionPenInference.generate_word()
    # This function just stores the session metadata
    return {
        "style_id": str(uuid4()),
        "embedding": [],
        "sample_count": len(image_paths),
        "image_paths": image_paths,
    }
