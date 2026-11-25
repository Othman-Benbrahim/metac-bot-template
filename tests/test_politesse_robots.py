"""robots.txt aux lignes vides dans un groupe et « Disallow: » vide (cas d'intellinews.com, 2026-11-25)."""
import politesse

ROBOTS = """User-agent: *

# Allow crawling of all content
Disallow:

Disallow: /user/
Disallow: /feed

User-agent: Googlebot-Image
Allow: /
"""


class _R:
    status_code = 200
    text = ROBOTS


class _C:
    def get(self, *a, **k):
        return _R()


def test_refus_apres_ligne_vide():
    politesse._ROBOTS.clear()
    assert politesse.autorise(_C(), "https://exemple.org/") is True
    assert politesse.autorise(_C(), "https://exemple.org/feed/") is False
    assert politesse.autorise(_C(), "https://exemple.org/user/x") is False
    politesse._ROBOTS.clear()
