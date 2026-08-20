import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from app.models.enrichment import EnrichWordRequest, WordNlpData
from app.routers.enrichment import enrich_word_endpoint, get_word_phonetics


class EnrichmentRoutesTest(unittest.TestCase):
    def test_legacy_enrich_endpoint_is_stateless(self):
        data = WordNlpData(
            zipf_frequency=5.2,
            is_top_1k=False,
            is_top_5k=True,
            is_top_10k=True,
            is_top_50k=True,
            pos_available=["n"],
            senses=[],
            synonyms=[],
            antonyms=[],
            hypernyms=[],
            derived_forms=[],
            verb_frames=[],
            examples=[],
            estimated_level="A2",
            suggested_priority=78,
            primary_definition="a greeting",
        )

        with patch("app.routers.enrichment.enrich_word", return_value=data):
            result = asyncio.run(
                enrich_word_endpoint(EnrichWordRequest(text="hello", word_id="legacy-id"))
            )

        self.assertTrue(result.success)
        self.assertEqual(result.data, data)
        self.assertFalse(result.db_updated)

    def test_phonetics_endpoint_only_returns_analysis(self):
        with patch(
            "app.routers.enrichment.fetch_phonetics",
            return_value={
                "phonetic_text": "/həˈləʊ/",
                "phonetic_audio_link": "https://audio.test/hello.mp3",
            },
        ):
            result = asyncio.run(get_word_phonetics("hello"))

        self.assertEqual(result.phonetic_text, "/həˈləʊ/")
        self.assertEqual(result.phonetic_audio_link, "https://audio.test/hello.mp3")

    def test_nlp_and_phonetics_run_in_the_threadpool(self):
        sentinel = WordNlpData(
            zipf_frequency=1,
            is_top_1k=False,
            is_top_5k=False,
            is_top_10k=False,
            is_top_50k=False,
            pos_available=[],
            senses=[],
            synonyms=[],
            antonyms=[],
            hypernyms=[],
            derived_forms=[],
            verb_frames=[],
            examples=[],
            estimated_level="A1",
            suggested_priority=1,
            primary_definition="",
        )
        with patch("app.routers.enrichment.run_in_threadpool", new_callable=AsyncMock) as run:
            run.side_effect = [sentinel, {"phonetic_text": "", "phonetic_audio_link": ""}]
            from app.routers.enrichment import get_word_nlp

            self.assertIs(asyncio.run(get_word_nlp("hello")), sentinel)
            asyncio.run(get_word_phonetics("hello"))

        self.assertEqual(run.await_count, 2)


if __name__ == "__main__":
    unittest.main()
