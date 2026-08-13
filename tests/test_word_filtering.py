import unittest
from unittest.mock import patch

from app.config import settings
from app.processors.text_analysis import analyze_text
from app.services.word_classifier import classify_sentences


def _words(response) -> set[str]:
    return {w for w, _ in response.words}


def _proper_nouns(response) -> set[str]:
    return {w for w, _ in response.excluded_words.proper_nouns}


def _unknown(response) -> set[str]:
    return {w for w, _ in response.excluded_words.unknown}


class WordFilteringTest(unittest.TestCase):
    def test_names_capitalized_mid_sentence_are_reported_as_proper_nouns(self):
        text = (
            "The engineer visited Rearden at the mill yesterday. "
            "Later the manager called Rearden about the steel contract. "
            "Everyone in the office admired Dagny and her stubborn courage. "
            "The board dismissed Dagny without a single honest reason."
        )

        response = analyze_text(text)

        self.assertIn("rearden", _proper_nouns(response))
        self.assertIn("dagny", _proper_nouns(response))
        self.assertNotIn("rearden", _words(response))
        self.assertNotIn("dagny", _words(response))

    def test_sentence_initial_word_is_not_treated_as_a_proper_noun(self):
        text = (
            "Bread is expensive in this small village. "
            "Bread was cheaper before the harvest failed. "
            "Bread remains the only food they can afford."
        )

        response = analyze_text(text)

        self.assertIn("bread", _words(response))
        self.assertNotIn("bread", _proper_nouns(response))

    def test_invented_word_without_lexical_support_becomes_unknown(self):
        # Both occurrences follow a determiner, so the only signal left is lexical.
        text = (
            "The machine produced a flurbish during the night. "
            "Nobody could explain the flurbish to the tired engineers."
        )

        response = analyze_text(text)

        self.assertIn("flurbish", _unknown(response))
        self.assertNotIn("flurbish", _words(response))
        self.assertNotIn("flurbish", _proper_nouns(response))

    def test_ordinary_words_stay_accepted(self):
        text = (
            "The engineer visited Rearden at the mill yesterday. "
            "Nobody could explain the flurbish to the tired engineers."
        )

        response = analyze_text(text)
        accepted = _words(response)

        for word in ("engineer", "mill", "yesterday", "explain", "tired", "the"):
            self.assertIn(word, accepted)

    def test_titlecased_heading_does_not_manufacture_proper_nouns(self):
        text = (
            "The Rise Of The Golden Harvest. "
            "The harvest was golden and the rise was slow."
        )

        response = analyze_text(text)

        self.assertIn("harvest", _words(response))
        self.assertIn("golden", _words(response))
        self.assertEqual(set(), _proper_nouns(response))

    def test_all_caps_shouting_does_not_manufacture_proper_nouns(self):
        text = (
            "He shouted STOP at the driver twice. "
            "She shouted STOP again from the corner."
        )

        response = analyze_text(text)

        self.assertIn("stop", _words(response))
        self.assertNotIn("stop", _proper_nouns(response))

    def test_counts_reconcile_with_the_returned_word_list(self):
        text = (
            "The engineer visited Rearden at the mill yesterday. "
            "Nobody could explain the flurbish to the tired engineers. "
            "Later the manager called Rearden about the steel contract."
        )

        response = analyze_text(text)

        self.assertEqual(response.total_words, sum(c for _, c in response.words))
        self.assertEqual(response.total_unique_words, len(response.words))
        self.assertEqual(
            response.total_unique_words_before_filter,
            response.total_unique_words
            + response.excluded_proper_noun_count
            + response.excluded_unknown_count,
        )
        self.assertGreater(response.total_words_before_filter, response.total_words)

    def test_disabled_flag_restores_previous_behaviour(self):
        # Taggart passes the lexical check on frequency alone, so only the
        # capitalisation rule can keep it out of the dictionary.
        text = (
            "The engineer visited Taggart at the mill yesterday. "
            "Later the manager called Taggart about the steel contract."
        )

        self.assertIn("taggart", _proper_nouns(analyze_text(text)))

        with patch.object(settings, "WORD_FILTER_ENABLED", False):
            response = analyze_text(text)

        self.assertIsNone(response.excluded_words)
        self.assertIsNone(response.excluded_proper_noun_count)
        self.assertIsNone(response.total_words_before_filter)
        self.assertIn("taggart", _words(response))

    def test_thresholds_are_configurable(self):
        sentences = [
            "The engineer visited Rearden at the mill yesterday.",
            "Later the manager called Rearden about the steel contract.",
        ]

        with patch.object(settings, "WORD_FILTER_PROPER_NOUN_MIN_OCCURRENCES", 5):
            classified = classify_sentences(sentences)

        self.assertNotIn("rearden", classified.proper_nouns)

    def test_ordinal_tails_are_not_collected_as_words(self):
        classified = classify_sentences(["The 16th regiment left on the 3rd of May."])

        for bucket in (classified.accepted, classified.proper_nouns, classified.unknown):
            self.assertNotIn("th", bucket)
            self.assertNotIn("rd", bucket)

    def test_single_letter_tokens_never_reach_the_buckets(self):
        classified = classify_sentences(["A dog and I walked."])

        for bucket in (classified.accepted, classified.proper_nouns, classified.unknown):
            self.assertNotIn("a", bucket)
            self.assertNotIn("i", bucket)


if __name__ == "__main__":
    unittest.main()
