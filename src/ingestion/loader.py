# Module de chargement de documents.
# Supporte : PDF natifs, PDF scannés (via OCR), fichiers Word (.docx), images.

from pathlib import Path
from collections import Counter
import re
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
from docx import Document as DocxDocument

# Configuration Tesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# si une page PDF contient moins de MIN_TEXT_LENGTH_THRESHOLD caractères de texte natif,
# on considère qu'elle est scannée (image) et on bascule sur l'OCR.
MIN_TEXT_LENGTH_THRESHOLD = 20

# Une ligne est considérée comme un en-tête/pied de page récurrent si elle apparaît
# (identique, après normalisation) sur au moins cette proportion des pages du document.
# 0.4 = la ligne doit apparaitre sur au moins 40% des pages pour être retirée.
REPEATED_LINE_THRESHOLD = 0.4

# Une ligne trop longue est rarement un en-tête/pied de page (souvent une vraie phrase
# du corps de texte qui se répète par coïncidence, ex. une formule récurrente) : on ne
# la considère comme "à nettoyer" que si elle reste courte, pour éviter de supprimer
# du contenu scientifique légitime.
MAX_REPEATED_LINE_LENGTH = 150


class ExtractedPage:
    """Représente le contenu extrait d'une page ou d'un document,
    avec ses métadonnées de traçabilité."""

    def __init__(self, text: str, source_file: str, page_number: int, method: str):
        self.text = text
        self.metadata = {
            "source_file": source_file,
            "page_number": page_number,
            "extraction_method": method,  # "native" ou "ocr"
        }


def _normalize_line(line: str) -> str:
    """
    Normalise une ligne pour la comparaison entre pages : supprime les espaces
    superflus et les chiffres isolés (numéros de page qui changent d'une page à
    l'autre), afin de détecter des motifs répétés même si un numéro varie.

    Exemple : "8 of 20" et "9 of 20" sont tous deux normalisés vers "# of 20",
    ce qui permet de les reconnaître comme le même motif de pied de page.
    """
    normalized = line.strip().lower()
    normalized = re.sub(r"\d+", "#", normalized)  # remplace tous les nombres par #
    normalized = re.sub(r"\s+", " ", normalized)  # espaces multiples -> un seul
    return normalized


def detect_repeated_lines(raw_pages_text: list[str]) -> set[str]:
    """
    Détecte les lignes (en-têtes, pieds de page, DOI, nom de revue, etc.) qui se
    répètent sur une proportion significative des pages d'un même document.

    Args:
        raw_pages_text: texte brut de chaque page du document (une entrée par page)

    Returns:
        Un ensemble de versions normalisées de lignes à supprimer.
    """
    if len(raw_pages_text) < 3:
        # Sur un document trop court, la notion de "motif répété" n'est pas fiable
        # (trop peu de pages pour distinguer un vrai pied de page d'une coïncidence).
        return set()

    line_counter = Counter()
    for page_text in raw_pages_text:
        # set() : on ne compte qu'une fois par page, même si la ligne apparaît
        # plusieurs fois sur une même page (rare mais possible).
        lines_on_this_page = set(
            _normalize_line(line)
            for line in page_text.split("\n")
            if line.strip() and len(line.strip()) <= MAX_REPEATED_LINE_LENGTH
        )
        line_counter.update(lines_on_this_page)

    min_occurrences = max(2, int(len(raw_pages_text) * REPEATED_LINE_THRESHOLD))

    repeated = {
        normalized_line
        for normalized_line, count in line_counter.items()
        if count >= min_occurrences
    }
    return repeated


def clean_page_text(page_text: str, repeated_lines: set[str]) -> str:
    """
    Supprime d'une page les lignes identifiées comme en-tête/pied de page récurrent.

    Args:
        page_text: texte brut de la page
        repeated_lines: ensemble des motifs (normalisés) à retirer,
                        produit par detect_repeated_lines()

    Returns:
        Le texte de la page nettoyé de ces motifs répétitifs.
    """
    if not repeated_lines:
        return page_text

    cleaned_lines = [
        line for line in page_text.split("\n")
        if _normalize_line(line) not in repeated_lines
    ]
    return "\n".join(cleaned_lines).strip()


def ocr_page_image(page: fitz.Page, dpi: int = 300, lang: str = "fra") -> str:
    """
    Convertit une page PDF en image haute résolution et applique l'OCR.

    Args:
        page: objet page PyMuPDF
        dpi: résolution du rendu (300 recommandé pour un bon compromis vitesse/qualité OCR)
        lang: langue Tesseract ("fra" pour français, "eng" pour anglais,
              "fra+eng" pour les deux)

    Returns:
        Le texte reconnu par OCR.
    """
    zoom = dpi / 72  # 72 DPI = résolution de base de PyMuPDF
    matrix = fitz.Matrix(zoom, zoom)
    pixmap = page.get_pixmap(matrix=matrix)

    image_bytes = pixmap.tobytes("png")
    image = Image.open(io.BytesIO(image_bytes))

    text = pytesseract.image_to_string(image, lang=lang)
    return text


def load_pdf(filepath: str, ocr_lang: str = "fra") -> list[ExtractedPage]:
    """
    Charge un fichier PDF, page par page.
    Détecte automatiquement si chaque page est du texte natif ou une image scannée,
    et applique l'OCR uniquement quand c'est nécessaire (plus rapide qu'un OCR systématique).
    Nettoie ensuite les en-têtes/pieds de page qui se répètent d'une page à l'autre
    (nom de revue, DOI, citation, numéro de page), afin d'éviter de polluer les chunks
    avec du bruit non informatif pour la recherche sémantique.

    Args:
        filepath: chemin vers le fichier PDF
        ocr_lang: langue pour l'OCR si besoin

    Returns:
        Liste d'objets ExtractedPage, un par page du document.
    """
    path = Path(filepath)
    raw_pages = []  # (text, method) avant nettoyage

    doc = fitz.open(filepath)
    for page_index, page in enumerate(doc):
        native_text = page.get_text().strip()

        if len(native_text) >= MIN_TEXT_LENGTH_THRESHOLD:
            raw_pages.append((native_text, "native"))
        else:
            print(f"  Page {page_index + 1} de {path.name} : peu/pas de texte natif -> OCR en cours...")
            ocr_text = ocr_page_image(page, lang=ocr_lang)
            raw_pages.append((ocr_text, "ocr"))

    doc.close()

    # Détection des motifs répétés à l'échelle du document entier (toutes pages confondues)
    repeated_lines = detect_repeated_lines([text for text, _ in raw_pages])
    if repeated_lines:
        print(f"  {len(repeated_lines)} motif(s) d'en-tête/pied de page détecté(s) et retiré(s) dans {path.name}")

    pages = []
    for page_index, (text, method) in enumerate(raw_pages):
        cleaned_text = clean_page_text(text, repeated_lines)
        pages.append(ExtractedPage(
            text=cleaned_text,
            source_file=path.name,
            page_number=page_index + 1,
            method=method
        ))

    return pages


def load_docx(filepath: str) -> list[ExtractedPage]:
    """
    Charge un fichier Word (.docx), découpé par sections (titres Heading 1/2/...)
    plutôt qu'en un seul bloc de texte.

    Les .docx n'ayant pas de pagination fixe (contrairement au PDF), on utilise
    les titres du document comme repère de traçabilité à la place du numéro de
    page : chaque section devient un ExtractedPage distinct, avec page_number
    utilisé comme numéro de section. Si le document ne contient aucun titre,
    tout le contenu est regroupé dans une seule section (comportement identique
    à l'ancienne version).

    Args:
        filepath: chemin vers le fichier .docx

    Returns:
        Liste d'ExtractedPage, une par section détectée (ou une seule si
        aucun titre n'est présent dans le document).
    """
    path = Path(filepath)
    doc = DocxDocument(filepath)

    sections = []
    current_section_title = "Introduction"
    current_section_text = []

    def flush_section():
        if current_section_text:
            sections.append((current_section_title, "\n".join(current_section_text)))

    for para in doc.paragraphs:
        if para.style.name.startswith("Heading"):
            flush_section()
            current_section_title = para.text.strip() or current_section_title
            current_section_text = []
        elif para.text.strip():
            current_section_text.append(para.text)

    # Tableaux ajoutés à la dernière section rencontrée (souvent en fin de
    # document, ou juste après le titre de section correspondant)
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text.strip() for cell in row.cells)
            if row_text.strip(" |"):
                current_section_text.append(row_text)

    flush_section()

    # Nettoyage des en-têtes/pieds de page récurrents : un .docx issu d'une
    # conversion PDF->Word (ex. via un outil en ligne) conserve souvent, comme
    # texte normal, les en-têtes/pieds de page du PDF d'origine (nom d'auteur,
    # numéro de page, DOI répété sur chaque "page" convertie). On applique donc
    # la même détection/nettoyage que pour les PDF, à l'échelle des sections.
    section_texts = [text for _, text in sections]
    repeated_lines = detect_repeated_lines(section_texts)
    if repeated_lines:
        print(f"  {len(repeated_lines)} motif(s) d'en-tête/pied de page détecté(s) et retiré(s) dans {path.name}")

    return [
        ExtractedPage(
            text=clean_page_text(section_text, repeated_lines),
            source_file=path.name,
            page_number=idx + 1,  # numéro de section en substitut de numéro de page
            method="native"
        )
        for idx, (title, section_text) in enumerate(sections)
    ]


def load_image(filepath: str, ocr_lang: str = "fra") -> list[ExtractedPage]:
    """
    Charge une image (JPG, PNG) et en extrait le texte par OCR.
    Utile si certains documents médicaux sont fournis sous forme de photos/scans isolés.

    Args:
        filepath: chemin vers l'image
        ocr_lang: langue pour l'OCR

    Returns:
        Liste contenant un seul ExtractedPage.
    """
    path = Path(filepath)
    image = Image.open(filepath)
    text = pytesseract.image_to_string(image, lang=ocr_lang)

    return [ExtractedPage(
        text=text,
        source_file=path.name,
        page_number=1,
        method="ocr"
    )]


def load_document(filepath: str, ocr_lang: str = "fra") -> list[ExtractedPage]:
    """
    Point d'entrée unique : détecte le type de fichier et appelle le bon loader.

    Args:
        filepath: chemin du fichier à charger
        ocr_lang: langue Tesseract pour l'OCR

    Returns:
        Liste d'ExtractedPage
    """
    path = Path(filepath)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return load_pdf(filepath, ocr_lang=ocr_lang)
    elif suffix == ".docx":
        return load_docx(filepath)
    elif suffix in [".png", ".jpg", ".jpeg"]:
        return load_image(filepath, ocr_lang=ocr_lang)
    else:
        raise ValueError(f"Format non supporté : {suffix}")


def load_all_documents(folder: str, ocr_lang: str = "fra") -> list[ExtractedPage]:
    """
    Charge tous les documents supportés d'un dossier.

    Args:
        folder: chemin du dossier contenant les documents
        ocr_lang: langue Tesseract pour l'OCR

    Returns:
        Liste combinée de toutes les pages extraites, tous documents confondus.
    """
    all_pages = []
    supported_extensions = [".pdf", ".docx", ".png", ".jpg", ".jpeg"]

    for filepath in sorted(Path(folder).glob("*")):
        if filepath.suffix.lower() in supported_extensions:
            print(f"Chargement de {filepath.name}...")
            pages = load_document(str(filepath), ocr_lang=ocr_lang)
            all_pages.extend(pages)
            print(f"  -> {len(pages)} page(s)/section(s) extraite(s)")

    print(f"\nTotal : {len(all_pages)} pages extraites depuis {folder}")
    return all_pages