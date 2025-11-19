import hashlib
import json
from typing import Optional, List, Any
import os
import re
import logging
from django.db import transaction
from .models import (
    Book,
    Thematique,
    Chapter,
    Section,
    Subsection,
    ThematiqueTranslation,
    ChapterTranslation,
    SectionTranslation,
    SubsectionTranslation,
    TranslationStatus,
)


def _norm(obj) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except Exception:
        return ""


def _hash_text(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        if p:
            h.update(p.encode("utf-8"))
            h.update(b"|")
    return h.hexdigest()


def _targets_for(source: str, provided: Optional[List[str]] = None) -> List[str]:
    if provided:
        return [t for t in provided if t in ("fr", "en", "pt") and t != source]
    langs = ["fr", "en", "pt"]
    return [l for l in langs if l != source]


def translate_book_sync(book_id: int, target_langs: Optional[List[str]] = None) -> None:
    book = Book.objects.get(id=book_id)
    source_lang = book.language or "fr"
    targets = _targets_for(source_lang, target_langs)
    client = LibreTranslateClient(os.getenv("LIBRETRANSLATE_URL", "http://localhost:5000"))

    with transaction.atomic():
        # Thematique
        for th in Thematique.objects.filter(book=book).all():
            sh = _hash_text(th.title or "", th.description or "")
            for tgt in targets:
                tr, _ = ThematiqueTranslation.objects.get_or_create(thematique=th, lang=tgt)
                if tr.source_hash != sh or not tr.title:
                    tr.source_hash = sh
                    # Traduire
                    title = _translate_safe(client, th.title, source_lang, tgt)
                    desc = _translate_safe(client, th.description, source_lang, tgt)
                    tr.title = title if title else tr.title
                    tr.description = desc if desc else tr.description
                    tr.status = TranslationStatus.READY if (tr.title or tr.description) else TranslationStatus.PENDING
                    tr.save()

        # Chapter
        for ch in Chapter.objects.filter(book=book).all():
            sh = _hash_text(ch.title or "", ch.content or "")
            for tgt in targets:
                tr, _ = ChapterTranslation.objects.get_or_create(chapter=ch, lang=tgt)
                if tr.source_hash != sh or not tr.title or not tr.content:
                    tr.source_hash = sh
                    tr.title = _translate_safe(client, ch.title, source_lang, tgt) or tr.title
                    tr.content = _translate_safe(client, ch.content, source_lang, tgt) or tr.content
                    tr.status = TranslationStatus.READY if (tr.title or tr.content) else TranslationStatus.PENDING
                    tr.save()

        # Section
        for se in Section.objects.filter(chapter__book=book).all():
            sh = _hash_text(se.title or "", se.content or "", _norm(se.images), _norm(se.tables))
            for tgt in targets:
                tr, _ = SectionTranslation.objects.get_or_create(section=se, lang=tgt)
                if tr.source_hash != sh or not tr.title or not tr.content:
                    tr.source_hash = sh
                    tr.title = _translate_safe(client, se.title, source_lang, tgt) or tr.title
                    tr.content = _translate_safe(client, se.content, source_lang, tgt) or tr.content
                    tr.images = _translate_images(client, se.images, source_lang, tgt)
                    tr.tables = _translate_tables(client, se.tables, source_lang, tgt)
                    tr.status = TranslationStatus.READY if (tr.title or tr.content or tr.images or tr.tables) else TranslationStatus.PENDING
                    tr.save()

        # Subsection
        for su in Subsection.objects.filter(section__chapter__book=book).all():
            sh = _hash_text(su.title or "", su.content or "", _norm(su.images), _norm(su.tables))
            for tgt in targets:
                tr, _ = SubsectionTranslation.objects.get_or_create(subsection=su, lang=tgt)
                if tr.source_hash != sh or not tr.title or not tr.content:
                    tr.source_hash = sh
                    tr.title = _translate_safe(client, su.title, source_lang, tgt) or tr.title
                    tr.content = _translate_safe(client, su.content, source_lang, tgt) or tr.content
                    tr.images = _translate_images(client, su.images, source_lang, tgt)
                    tr.tables = _translate_tables(client, su.tables, source_lang, tgt)
                    tr.status = TranslationStatus.READY if (tr.title or tr.content or tr.images or tr.tables) else TranslationStatus.PENDING
                    tr.save()


class LibreTranslateClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = os.getenv('LIBRETRANSLATE_API_KEY')

    def translate(self, text: str, source: str, target: str) -> Optional[str]:
        if not text or source == target:
            return text
        try:
            # Use requests if available
            try:
                import requests
            except Exception:
                logging.warning("requests not available; skipping translation")
                return None
            payload = {
                'q': text,
                'source': source,
                'target': target,
                'format': 'text',
            }
            if self.api_key:
                payload['api_key'] = self.api_key
            resp = requests.post(f"{self.base_url}/translate", data=payload, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                # LibreTranslate returns {"translatedText": "..."}
                if isinstance(data, dict) and 'translatedText' in data:
                    return data['translatedText']
                # Some variants may return string
                if isinstance(data, str):
                    return data
            logging.warning("LibreTranslate HTTP %s: %s", resp.status_code, resp.text[:200])
        except Exception as e:
            logging.warning("LibreTranslate error: %s", e)
        return None


PLACEHOLDER_RE = re.compile(r"\{\{[^}]+\}\}")


def _mask_placeholders(text: str):
    # Replace placeholders with tokens to protect them during translation
    if not text:
        return text, {}
    mapping = {}
    def repl(m):
        token = f"__PH_{len(mapping)}__"
        mapping[token] = m.group(0)
        return token
    masked = PLACEHOLDER_RE.sub(repl, text)
    return masked, mapping


def _unmask_placeholders(text: str, mapping: dict):
    if not text:
        return text
    for token, orig in mapping.items():
        text = text.replace(token, orig)
    return text


def _translate_safe(client: 'LibreTranslateClient', text: Optional[str], source: str, target: str) -> Optional[str]:
    if not text:
        return text
    masked, mapping = _mask_placeholders(text)
    out = client.translate(masked, source, target)
    return _unmask_placeholders(out, mapping) if out is not None else None


def _translate_images(client: 'LibreTranslateClient', images: Any, source: str, target: str) -> Any:
    # images expected as list of dicts with optional 'caption'
    try:
        if not isinstance(images, list):
            return images
        out = []
        for img in images:
            if isinstance(img, dict):
                new = dict(img)
                if 'caption' in new and isinstance(new['caption'], str):
                    tr = _translate_safe(client, new['caption'], source, target)
                    if tr:
                        new['caption'] = tr
                out.append(new)
            else:
                out.append(img)
        return out
    except Exception:
        return images


def _translate_tables(client: 'LibreTranslateClient', tables: Any, source: str, target: str) -> Any:
    # Recursively translate string leaves inside table JSON (could be list/dict)
    def rec(x):
        if isinstance(x, str):
            return _translate_safe(client, x, source, target) or x
        if isinstance(x, list):
            return [rec(v) for v in x]
        if isinstance(x, dict):
            return {k: rec(v) for k, v in x.items()}
        return x
    try:
        return rec(tables)
    except Exception:
        return tables
