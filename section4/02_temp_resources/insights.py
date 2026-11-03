saved = {}


def analyze(transcript):
    return {"summary": transcript}


def save_insights(post_id, insights):
    saved[post_id] = insights
