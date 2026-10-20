"""Local screening first; optional AI never removes usable screened portfolios."""
from .ranking import build_ranked
from .simple_ai import refine


def recommend(prompt,names,evidence,api_key="",model=""):
    base=build_ranked(prompt,names,evidence,model)
    return refine(base,api_key,model) if api_key and model else base
