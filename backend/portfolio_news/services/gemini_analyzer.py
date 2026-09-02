import logging

from dataclasses import dataclass

from typing import Optional

import requests

from ai.views import (
    GEMINI_API_BASE,
    extract_response_text,
    get_gemini_api_key,
    get_gemini_model,
)

from ..constants import (
    ImpactLevel,
    Materiality,
    NewsCategory,
    Sentiment,
    TimeHorizon,
)


logger = logging.getLogger(__name__)


REQUEST_TIMEOUT_SECONDS = 30


SYSTEM_INSTRUCTIONS = """
You are the news-analysis component of the Personal Wealth
Monitoring System (PWMS) Portfolio News Intelligence agent.

You will be given ONE news article's metadata (headline,
snippet, source, publish time) and ONE holding from the
user's real PWMS portfolio that a deterministic filter has
already matched to this article.

Your job is to assess whether the article is materially
relevant to that specific holding, and if so, how.

IMPORTANT RULES:

1. Base your assessment ONLY on the supplied article headline
   and snippet, and the supplied holding information. Never
   invent facts, figures, or events not present in what you
   were given.

2. If the snippet does not contain enough information to
   support a confident assessment, say so plainly (lower
   confidence, relevance_score, and impact_score accordingly)
   rather than guessing.

3. This is NOT investment advice. Never tell the user to buy,
   sell, hold, or take any specific action. Never guarantee or
   predict returns. Use hedged language such as "potential
   impact", "may affect", "based on the available article".

4. relevance_score and impact_score are integers from 0 to 100.
   confidence is a float from 0.0 to 1.0.

5. impact reflects the potential magnitude of the news for
   THIS holding specifically, not the market in general.

6. summary must be a short, factual, 1-2 sentence summary of
   what the article actually says - not speculation.

7. portfolio_implication and reason must clearly be framed as
   an AI assessment, not a certainty.

8. Respond with ONLY the JSON object described by the response
   schema. No prose, no markdown fences, nothing else.

9. materiality is your judgment of how significant the reported
   event is IN ITS OWN RIGHT (independent of how large this
   holding is in the user's portfolio) - "if this is true, how
   big a deal is it for this company/sector": trivial, low,
   moderate, high, or critical.

10. You MUST separate what the source explicitly states from
    what it could mean:
    - key_facts: only statements the article snippet directly
      and explicitly reports. No inference, no speculation. If
      the snippet gives you very little to work with, key_facts
      should be short and say so rather than padding it out.
    - interpretation: what this event could plausibly mean for
      the company/sector/portfolio. Clearly speculative, hedged
      language required ("could", "may", "this may suggest").
      Never state interpretation as if it were a fact.
    - uncertainty_notes: what is NOT known from the snippet that
      would matter for a fuller assessment (e.g. exact financial
      figures, timeline, regulatory finality, management
      confirmation). If the snippet is unusually complete, it is
      fine for this to be brief, but do not leave it empty just
      to seem confident - name at least one real unknown when
      one exists.
"""


ARTICLE_ANALYSIS_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "relevant": {"type": "BOOLEAN"},
        "relevance_score": {"type": "INTEGER"},
        "sentiment": {
            "type": "STRING",
            "enum": [choice.value for choice in Sentiment],
        },
        "impact": {
            "type": "STRING",
            "enum": [choice.value for choice in ImpactLevel],
        },
        "impact_score": {"type": "INTEGER"},
        "category": {
            "type": "STRING",
            "enum": [choice.value for choice in NewsCategory],
        },
        "time_horizon": {
            "type": "STRING",
            "enum": [choice.value for choice in TimeHorizon],
        },
        "summary": {"type": "STRING"},
        "portfolio_implication": {"type": "STRING"},
        "reason": {"type": "STRING"},
        "confidence": {"type": "NUMBER"},
        "materiality": {
            "type": "STRING",
            "enum": [choice.value for choice in Materiality],
        },
        "key_facts": {"type": "STRING"},
        "interpretation": {"type": "STRING"},
        "uncertainty_notes": {"type": "STRING"},
    },
    "required": [
        "relevant",
        "relevance_score",
        "sentiment",
        "impact",
        "impact_score",
        "category",
        "time_horizon",
        "summary",
        "portfolio_implication",
        "reason",
        "confidence",
        "materiality",
        "key_facts",
        "interpretation",
        "uncertainty_notes",
    ],
}


def _clamp_int(value, low, high, default):
    try:
        return max(low, min(high, int(value)))
    except (TypeError, ValueError):
        return default


def _clamp_float(value, low, high, default):
    try:
        return max(low, min(high, float(value)))
    except (TypeError, ValueError):
        return default


def _validate_choice(value, valid_values, default):
    if isinstance(value, str) and value in valid_values:
        return value

    return default


@dataclass
class ArticleAnalysis:
    """
    Validated result of analyzing one article against one
    holding. Every field is defensively clamped/validated
    against what Gemini returned - the AI's output is never
    trusted blindly, per PWMS's rule that the AI interprets
    but does not author authoritative values.
    """

    relevant: bool
    relevance_score: int
    sentiment: str
    impact: str
    impact_score: int
    category: str
    time_horizon: str
    summary: str
    portfolio_implication: str
    reason: str
    confidence: float
    materiality: str = Materiality.MODERATE
    key_facts: str = ""
    interpretation: str = ""
    uncertainty_notes: str = ""

    @classmethod
    def from_gemini_json(cls, data: dict) -> "ArticleAnalysis":

        impact_score = _clamp_int(
            data.get("impact_score"), 0, 100, 0
        )

        valid_sentiments = {choice.value for choice in Sentiment}

        valid_impacts = {choice.value for choice in ImpactLevel}

        valid_categories = {
            choice.value for choice in NewsCategory
        }

        valid_horizons = {
            choice.value for choice in TimeHorizon
        }

        valid_materialities = {
            choice.value for choice in Materiality
        }

        impact = _validate_choice(
            data.get("impact"),
            valid_impacts,
            ImpactLevel.from_score(impact_score),
        )

        return cls(
            relevant=bool(data.get("relevant", False)),
            relevance_score=_clamp_int(
                data.get("relevance_score"), 0, 100, 0
            ),
            sentiment=_validate_choice(
                data.get("sentiment"),
                valid_sentiments,
                Sentiment.NEUTRAL,
            ),
            impact=impact,
            impact_score=impact_score,
            category=_validate_choice(
                data.get("category"),
                valid_categories,
                NewsCategory.OTHER,
            ),
            time_horizon=_validate_choice(
                data.get("time_horizon"),
                valid_horizons,
                TimeHorizon.UNSPECIFIED,
            ),
            summary=(
                str(data.get("summary", "")).strip()
                or "The AI did not provide a summary for this article."
            ),
            portfolio_implication=(
                str(
                    data.get("portfolio_implication", "")
                ).strip()
                or (
                    "The AI could not determine a specific "
                    "portfolio implication from this article."
                )
            ),
            reason=(
                str(data.get("reason", "")).strip()
                or "No reason was provided by the AI."
            ),
            confidence=_clamp_float(
                data.get("confidence"), 0.0, 1.0, 0.0
            ),
            materiality=_validate_choice(
                data.get("materiality"),
                valid_materialities,
                # A missing/invalid materiality defaults from the
                # impact_level, so it degrades sensibly rather than
                # silently becoming "moderate" for a critical story.
                {
                    ImpactLevel.CRITICAL: Materiality.CRITICAL,
                    ImpactLevel.HIGH: Materiality.HIGH,
                    ImpactLevel.MODERATE: Materiality.MODERATE,
                    ImpactLevel.LOW: Materiality.LOW,
                    ImpactLevel.VERY_LOW: Materiality.TRIVIAL,
                }.get(impact, Materiality.MODERATE),
            ),
            key_facts=str(data.get("key_facts", "")).strip(),
            interpretation=str(
                data.get("interpretation", "")
            ).strip(),
            uncertainty_notes=str(
                data.get("uncertainty_notes", "")
            ).strip(),
        )


class GeminiArticleAnalyzer:
    """
    Analyzes one (article, holding) pair using the same Gemini
    REST integration as the existing PWMS chatbot (ai/views.py)
    - same API key/model resolution, same endpoint - just a
    different prompt and structured-JSON output instead of
    free text.

    Never raises: any failure (missing key, network, timeout,
    malformed response) is logged and returns None so a single
    bad analysis cannot stop the monitoring run.
    """

    def _build_payload(self, article, holding):

        holding_context = {
            "holding_type": holding.holding_type,
            "display_name": holding.display_name,
            "symbol": holding.symbol or None,
            "amc_name": holding.amc_name or None,
            "portfolio_weight_percent": round(
                holding.portfolio_weight, 2
            ),
        }

        article_context = {
            "title": article.title,
            "description": article.description,
            "source": article.source,
            "published_at": (
                article.published_at.isoformat()
                if article.published_at
                else None
            ),
        }

        user_content = (
            "HOLDING:\n"
            f"{holding_context}\n\n"
            "ARTICLE:\n"
            f"{article_context}"
        )

        return {
            "system_instruction": {
                "parts": [{"text": SYSTEM_INSTRUCTIONS}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_content}],
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": (
                    ARTICLE_ANALYSIS_RESPONSE_SCHEMA
                ),
            },
        }

    def analyze(
        self,
        article,
        holding,
        user=None,
    ) -> Optional[ArticleAnalysis]:

        api_key = get_gemini_api_key()

        if not api_key:
            logger.warning(
                "GeminiArticleAnalyzer: no Gemini API key "
                "configured, skipping analysis."
            )
            return None

        payload = self._build_payload(article, holding)

        model = get_gemini_model()

        gemini_url = f"{GEMINI_API_BASE}/{model}:generateContent"

        try:
            response = requests.post(
                gemini_url,
                headers={
                    "x-goog-api-key": api_key,
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )

            response.raise_for_status()

            data = response.json()
            
            usage = data.get("usageMetadata", {})

            logger.info(
                "Gemini usage | article=%s | holding=%r | "
                "input=%s | output=%s | total=%s | cached=%s",
                getattr(article, "id", None),
                holding.display_name,
                usage.get("promptTokenCount", 0),
                usage.get("candidatesTokenCount", 0),
                usage.get("totalTokenCount", 0),
                usage.get("cachedContentTokenCount", 0),
            )

            from ai.services.usage_tracking import (
                record_gemini_usage,
            )

            try:
                record_gemini_usage(
                    user=user,
                    endpoint="article_analysis",
                    model_name=model,
                    usage_metadata=usage,
                )
            except Exception:
                # Same defense-in-depth as portfolio_chat: the
                # article analysis below must proceed even if
                # usage tracking somehow raises past its own
                # internal safety net.
                logger.exception(
                    "record_gemini_usage raised unexpectedly "
                    "for article_analysis; continuing without it."
                )

            raw_text = extract_response_text(data)

            if not raw_text:
                logger.warning(
                    "GeminiArticleAnalyzer: empty response for "
                    "article id=%s holding=%r",
                    getattr(article, "id", None),
                    holding.display_name,
                )
                return None

            import json as json_module

            parsed = json_module.loads(raw_text)

            return ArticleAnalysis.from_gemini_json(parsed)

        except requests.exceptions.RequestException as exc:
            logger.warning(
                "GeminiArticleAnalyzer: request failed for "
                "article id=%s holding=%r: %s",
                getattr(article, "id", None),
                holding.display_name,
                exc,
            )
            return None

        except (ValueError, KeyError, TypeError) as exc:
            # Covers JSON decode errors and unexpected shapes.
            logger.warning(
                "GeminiArticleAnalyzer: could not parse response "
                "for article id=%s holding=%r: %s",
                getattr(article, "id", None),
                holding.display_name,
                exc,
            )
            return None