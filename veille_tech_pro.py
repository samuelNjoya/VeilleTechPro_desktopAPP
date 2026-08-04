#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VEILLE TECH PRO - Application de veille technologique avec IA Groq
Version : 2.0.0
Auteur : VeilleTech
Licence : MIT

Description :
    Application desktop pour la veille technologique.
    Lecture de flux RSS, résumé par IA (Groq) en français ou anglais.
    Interface professionnelle avec configuration persistante.
"""

# ============================================================================
# IMPORTS
# ============================================================================

import os
import sys
import json
import sqlite3
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Variables d'environnement
from dotenv import load_dotenv

# Tiers
import feedparser
import requests
from bs4 import BeautifulSoup
from groq import Groq

# Interface graphique
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# ============================================================================
# CONSTANTES
# ============================================================================

APP_NAME = "Veille Tech Pro"
APP_VERSION = "2.0.0"
APP_AUTHOR = "VeilleTech"

# Dossiers
BASE_DIR = Path(__file__).parent
DATA_DIR = Path.home() / ".veille_tech"
LOCALES_DIR = BASE_DIR / "locales"
ASSETS_DIR = BASE_DIR / "assets" / "icons"

# Fichiers
CONFIG_FILE = DATA_DIR / "config.json"
DB_FILE = DATA_DIR / "articles.db"

# Création des dossiers
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# GESTIONNAIRE DE CONFIGURATION
# ============================================================================

class ConfigManager:
    """Gestionnaire de configuration persistante."""
    
    DEFAULT_CONFIG = {
        "language": "fr",
        "max_articles_per_feed": 5,
        "api_key": "",
        "feeds": [
            {"url": "https://news.ycombinator.com/rss", "enabled": True, "category": "tech"},
            {"url": "https://github.blog/feed/", "enabled": True, "category": "tech"},
            {"url": "https://www.reddit.com/r/programming/.rss", "enabled": True, "category": "tech"},
            {"url": "https://www.lemonde.fr/rss/feed.xml", "enabled": True, "category": "news"},
            {"url": "https://www.lefigaro.fr/rss/figaro_actualites.xml", "enabled": True, "category": "news"},
            {"url": "https://www.20minutes.fr/feed/rss", "enabled": True, "category": "news"},
            {"url": "https://www.theverge.com/rss/index.xml", "enabled": True, "category": "tech"},
            {"url": "https://techcrunch.com/feed/", "enabled": True, "category": "tech"},
            {"url": "https://arstechnica.com/feed/", "enabled": True, "category": "tech"},
            {"url": "https://www.nature.com/nature.rss", "enabled": True, "category": "science"},
        ],
        "summary_length": "long"  # "short" | "medium" | "long"
    }
    
    def __init__(self):
        self.config = self.load()
    
    def load(self) -> Dict:
        """Charge la configuration depuis le fichier."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # Fusion avec les valeurs par défaut
                    for key, value in self.DEFAULT_CONFIG.items():
                        if key not in config:
                            config[key] = value
                    return config
            except Exception:
                pass
        return self.DEFAULT_CONFIG.copy()
    
    def save(self) -> None:
        """Sauvegarde la configuration."""
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Erreur sauvegarde config : {e}")
    
    def get(self, key: str, default=None):
        """Récupère une valeur de configuration."""
        return self.config.get(key, default)
    
    def set(self, key: str, value) -> None:
        """Définit une valeur de configuration."""
        self.config[key] = value
        self.save()
    
    def get_feeds(self) -> List[Dict]:
        """Récupère la liste des flux RSS."""
        return self.config.get("feeds", [])
    
    def add_feed(self, url: str, category: str = "general") -> None:
        """Ajoute un flux RSS."""
        if url not in [f["url"] for f in self.config["feeds"]]:
            self.config["feeds"].append({
                "url": url,
                "enabled": True,
                "category": category
            })
            self.save()
    
    def remove_feed(self, url: str) -> None:
        """Supprime un flux RSS."""
        self.config["feeds"] = [f for f in self.config["feeds"] if f["url"] != url]
        self.save()
    
    def get_language(self) -> str:
        """Récupère la langue sélectionnée."""
        return self.config.get("language", "fr")
    
    def set_language(self, lang: str) -> None:
        """Définit la langue."""
        if lang in ["fr", "en"]:
            self.config["language"] = lang
            self.save()
    
    def get_max_articles(self) -> int:
        """Récupère le nombre max d'articles par flux."""
        return self.config.get("max_articles_per_feed", 5)

# ============================================================================
# GESTIONNAIRE DE LANGUE
# ============================================================================

class LanguageManager:
    """Gestionnaire de traductions multilingues."""
    
    def __init__(self, language: str = "fr"):
        self.language = language
        self.translations = self.load_language(language)
    
    def load_language(self, lang_code: str) -> Dict:
        """Charge les traductions pour une langue donnée."""
        lang_file = LOCALES_DIR / f"{lang_code}.json"
        
        # Fallback si le fichier n'existe pas
        if not lang_file.exists():
            lang_file = LOCALES_DIR / "fr.json"
        
        try:
            with open(lang_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {"app_title": "Veille Tech Pro"}
    
    def get(self, key: str, **kwargs) -> str:
        """Récupère une traduction avec formatage."""
        text = self.translations.get(key, key)
        if kwargs:
            text = text.format(**kwargs)
        return text
    
    def switch(self, lang_code: str) -> None:
        """Change la langue."""
        if lang_code in ["fr", "en"]:
            self.language = lang_code
            self.translations = self.load_language(lang_code)

# ============================================================================
# GESTIONNAIRE DE BASE DE DONNÉES
# ============================================================================

class DatabaseManager:
    """Gestionnaire de la base de données SQLite."""
    
    def __init__(self):
        self.db_path = DB_FILE
        self.conn = None
        self.cursor = None
        self.connect()
    
    def connect(self) -> None:
        """Établit la connexion à la base de données."""
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self) -> None:
        """Crée les tables si elles n'existent pas."""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                summary_fr TEXT,
                summary_en TEXT,
                source TEXT,
                date_published TIMESTAMP,
                date_scanned TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                category TEXT,
                read INTEGER DEFAULT 0,
                favorite INTEGER DEFAULT 0
            )
        ''')
        
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_articles_date 
            ON articles(date_scanned DESC)
        ''')
        
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_articles_source 
            ON articles(source)
        ''')
        
        self.conn.commit()
    
    def save_article(self, article: Dict) -> None:
        """Sauvegarde ou met à jour un article."""
        self.cursor.execute('''
            INSERT OR REPLACE INTO articles 
            (id, title, url, summary_fr, summary_en, source, date_published, category, date_scanned)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            article.get('id'),
            article.get('title', ''),
            article.get('url', ''),
            article.get('summary_fr', ''),
            article.get('summary_en', ''),
            article.get('source', ''),
            article.get('date_published'),
            article.get('category', '')
        ))
        self.conn.commit()
    
    def get_article(self, article_id: str) -> Optional[Dict]:
        """Récupère un article par son ID."""
        self.cursor.execute(
            "SELECT * FROM articles WHERE id = ?",
            (article_id,)
        )
        row = self.cursor.fetchone()
        if row:
            columns = [description[0] for description in self.cursor.description]
            return dict(zip(columns, row))
        return None
    
    def get_articles(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Récupère tous les articles triés par date."""
        self.cursor.execute('''
            SELECT * FROM articles 
            ORDER BY date_scanned DESC 
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        columns = [description[0] for description in self.cursor.description]
        return [dict(zip(columns, row)) for row in self.cursor.fetchall()]
    
    def search_articles(self, query: str) -> List[Dict]:
        """Recherche des articles par titre ou résumé."""
        self.cursor.execute('''
            SELECT * FROM articles 
            WHERE title LIKE ? OR summary_fr LIKE ? OR summary_en LIKE ?
            ORDER BY date_scanned DESC
        ''', (f'%{query}%', f'%{query}%', f'%{query}%'))
        columns = [description[0] for description in self.cursor.description]
        return [dict(zip(columns, row)) for row in self.cursor.fetchall()]
    
    def delete_article(self, article_id: str) -> None:
        """Supprime un article."""
        self.cursor.execute("DELETE FROM articles WHERE id = ?", (article_id,))
        self.conn.commit()
    
    def clear_articles(self) -> None:
        """Supprime tous les articles."""
        self.cursor.execute("DELETE FROM articles")
        self.conn.commit()
    
    def get_article_count(self) -> int:
        """Récupère le nombre total d'articles."""
        self.cursor.execute("SELECT COUNT(*) FROM articles")
        return self.cursor.fetchone()[0]
    
    def close(self) -> None:
        """Ferme la connexion à la base de données."""
        if self.conn:
            self.conn.close()
    
    def __del__(self):
        self.close()

# ============================================================================
# GESTIONNAIRE DE SCAN (RSS + IA)
# ============================================================================

class ScanManager:
    """Gestionnaire de scan des flux RSS et de résumé IA."""
    
    def __init__(self, config_manager: ConfigManager, db_manager: DatabaseManager):
        self.config = config_manager
        self.db = db_manager
        self.client = None
        self.lang_manager = None
        self.is_running = False
        self.progress_callback = None
        self.status_callback = None
        self.article_callback = None
        self.complete_callback = None
    
    def initialize_api(self, api_key: str) -> bool:
        """Initialise le client Groq avec la clé API."""
        try:
            self.client = Groq(api_key=api_key)
            # Test de connexion
            self.client.chat.completions.create(
                messages=[{"role": "user", "content": "Test"}],
                model="llama-3.1-8b-instant",
                max_tokens=5
            )
            return True
        except Exception as e:
            print(f"Erreur Groq : {e}")
            self.client = None
            return False
    
    def set_language(self, lang_manager: LanguageManager) -> None:
        """Définit le gestionnaire de langue."""
        self.lang_manager = lang_manager
    
    def set_callbacks(self, progress=None, status=None, article=None, complete=None) -> None:
        """Définit les callbacks pour la progression."""
        self.progress_callback = progress
        self.status_callback = status
        self.article_callback = article
        self.complete_callback = complete
    
    def scan_all(self) -> None:
        """Lance le scan de tous les flux RSS."""
        if self.is_running:
            return
        
        if not self.client:
            raise ValueError("API Groq non initialisée")
        
        if not self.lang_manager:
            raise ValueError("Gestionnaire de langue non défini")
        
        self.is_running = True
        threading.Thread(target=self._scan_thread, daemon=True).start()
    
    def _scan_thread(self) -> None:
        """Thread de scan."""
        try:
            feeds = self.config.get_feeds()
            max_articles = self.config.get_max_articles()
            lang = self.config.get_language()
            
            total_feeds = len(feeds)
            total_articles = 0
            new_articles = 0
            
            for idx, feed_config in enumerate(feeds):
                if not feed_config.get("enabled", True):
                    continue
                
                feed_url = feed_config.get("url", "")
                category = feed_config.get("category", "general")
                
                self._update_status(f"Lecture : {feed_url[:60]}...")
                self._update_progress((idx / total_feeds) * 100)
                
                try:
                    feed = feedparser.parse(feed_url)
                    feed_title = feed.feed.get("title", "Source inconnue")
                    
                    for entry in feed.entries[:max_articles]:
                        article_url = entry.get("link", "")
                        if not article_url:
                            continue
                        
                        article_id = article_url
                        existing = self.db.get_article(article_id)
                        
                        if existing:
                            # Article déjà existant
                            if lang == "fr":
                                summary = existing.get("summary_fr", existing.get("summary_en", ""))
                            else:
                                summary = existing.get("summary_en", existing.get("summary_fr", ""))
                            
                            self._add_article_to_display({
                                "id": article_id,
                                "title": entry.get("title", "Sans titre"),
                                "source": feed_title,
                                "summary": summary,
                                "date": entry.get("published", "")[:10],
                                "url": article_url
                            })
                        else:
                            # Nouvel article - extraction et résumé
                            content = self._fetch_article_content(article_url)
                            
                            if content and len(content) > 100:
                                # Résumé dans les deux langues
                                summary_fr = self._summarize(content, entry.get("title", ""), "fr")
                                summary_en = self._summarize(content, entry.get("title", ""), "en")
                                
                                # Sauvegarde
                                article_data = {
                                    "id": article_id,
                                    "title": entry.get("title", "Sans titre"),
                                    "url": article_url,
                                    "summary_fr": summary_fr,
                                    "summary_en": summary_en,
                                    "source": feed_title,
                                    "date_published": entry.get("published", datetime.now().isoformat()),
                                    "category": category
                                }
                                self.db.save_article(article_data)
                                
                                # Affichage
                                summary = summary_fr if lang == "fr" else summary_en
                                self._add_article_to_display({
                                    "id": article_id,
                                    "title": entry.get("title", "Sans titre"),
                                    "source": feed_title,
                                    "summary": summary,
                                    "date": entry.get("published", "")[:10],
                                    "url": article_url
                                })
                                new_articles += 1
                            else:
                                # Contenu trop court
                                self._add_article_to_display({
                                    "id": article_id,
                                    "title": entry.get("title", "Sans titre"),
                                    "source": feed_title,
                                    "summary": self.lang_manager.get("error_no_content") if self.lang_manager else "Contenu inaccessible",
                                    "date": entry.get("published", "")[:10],
                                    "url": article_url
                                })
                        
                        total_articles += 1
                
                except Exception as e:
                    print(f"Erreur flux {feed_url}: {e}")
                    self._update_status(f"Erreur : {feed_url[:40]}...")
            
            # Fin du scan
            self.is_running = False
            message = self.lang_manager.get("status_scan_done", count=new_articles)
            self._update_status(message)
            self._update_progress(100)
            
            if self.complete_callback:
                self.complete_callback(total_articles, new_articles)
                
        except Exception as e:
            self.is_running = False
            self._update_status(f"Erreur : {str(e)[:80]}")
    
    def _fetch_article_content(self, url: str) -> str:
        """Extrait le contenu d'un article depuis son URL."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Suppression des éléments inutiles
            for element in soup(["script", "style", "nav", "footer", "header", "aside", "iframe"]):
                element.decompose()
            
            # Recherche du contenu principal
            content = soup.find('article') or soup.find('main') or soup.find('body')
            
            if content:
                text = content.get_text()
            else:
                text = soup.get_text()
            
            # Nettoyage
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text[:4000]
        except Exception as e:
            print(f"Erreur extraction {url}: {e}")
            return ""
    
    def _summarize(self, text: str, title: str, lang: str) -> str:
        """Résume un article avec Groq."""
        if not self.client or not text or len(text) < 100:
            return "Contenu trop court ou inaccessible"
        
        try:
            # Prompt adapté à la langue
            if lang == "fr":
                system_prompt = "Tu es un expert en synthèse d'information. Tu produis des résumés détaillés et structurés de 300 à 400 mots en français."
                user_prompt = f"""Résume l'article suivant en français, en 300 à 400 mots, de manière claire et structurée.

Titre : {title}

Contenu :
{text[:3000]}

Résumé structuré (300-400 mots) :"""
            else:
                system_prompt = "You are an expert in information synthesis. You produce detailed and structured summaries of 300 to 400 words in English."
                user_prompt = f"""Summarize the following article in English, 300 to 400 words, clearly and structured.

Title: {title}

Content:
{text[:3000]}

Structured summary (300-400 words):"""
            
            completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model="llama-3.1-8b-instant",
                temperature=0.3,
                max_tokens=800
            )
            
            summary = completion.choices[0].message.content.strip()
            return summary if summary else "Résumé généré vide"
            
        except Exception as e:
            return f"Erreur Groq: {str(e)[:80]}"
    
    def _update_status(self, message: str) -> None:
        """Met à jour le statut via le callback."""
        if self.status_callback:
            self.status_callback(message)
    
    def _update_progress(self, value: float) -> None:
        """Met à jour la progression via le callback."""
        if self.progress_callback:
            self.progress_callback(value)
    
    def _add_article_to_display(self, article: Dict) -> None:
        """Ajoute un article à l'affichage via le callback."""
        if self.article_callback:
            self.article_callback(article)

# ============================================================================
# FENÊTRE PRINCIPALE
# ============================================================================

class MainWindow:
    """Fenêtre principale de l'application."""
    
    def __init__(self):
        # Gestionnaires
        self.config = ConfigManager()
        self.db = DatabaseManager()
        self.lang = LanguageManager(self.config.get_language())
        self.scanner = ScanManager(self.config, self.db)
        self.scanner.set_language(self.lang)
        
        # Configuration de la fenêtre
        self.root = tk.Tk()
        self.root.title(self.lang.get("app_title"))
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)
        
        # Icône (si disponible)
        icon_path = ASSETS_DIR / "app_icon.ico"
        if icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except Exception:
                pass
        
        # Style
        self._setup_styles()
        
        # Interface
        self._setup_ui()
        
        # Raccourcis clavier
        self._setup_shortcuts()
        
        # Variables
        self.articles = []
        self.current_filters = ""
        
        # Initialisation de l'API
        self._initialize_api()
        
        # Chargement des flux
        self._load_feeds()
        
        # Callbacks du scanner
        self.scanner.set_callbacks(
            progress=self._on_scan_progress,
            status=self._on_scan_status,
            article=self._on_article_found,
            complete=self._on_scan_complete
        )
    
    def _setup_styles(self) -> None:
        """Configure les styles de l'interface."""
        style = ttk.Style()
        style.theme_use("clam")
        
        # Palette de couleurs
        primary = "#0078D4"
        primary_dark = "#005A9E"
        bg_main = "#F5F6F8"
        bg_card = "#FFFFFF"
        text_primary = "#1A1A2E"
        text_secondary = "#6B7280"
        
        self.root.configure(bg=bg_main)
        
        # Style des boutons
        style.configure("Accent.TButton", 
                       background=primary, 
                       foreground="white",
                       borderwidth=0,
                       focusthickness=0,
                       padding=8)
        style.map("Accent.TButton",
                 background=[("active", primary_dark), ("pressed", primary_dark)])
        
        # Style des frames
        style.configure("Card.TFrame", background=bg_card)
        style.configure("Main.TFrame", background=bg_main)
        
        # Style des labels
        style.configure("Header.TLabel", 
                       font=("Segoe UI", 12, "bold"),
                       background=bg_card,
                       foreground=text_primary)
        
        style.configure("Status.TLabel",
                       font=("Segoe UI", 9),
                       background=bg_main,
                       foreground=text_secondary)
    
    def _setup_shortcuts(self) -> None:
        """Configure les raccourcis clavier."""
        self.root.bind('<Control-s>', lambda e: self._start_scan())
        self.root.bind('<Control-e>', lambda e: self._export_articles())
        self.root.bind('<Control-o>', lambda e: self._open_article())
        self.root.bind('<Control-q>', lambda e: self.root.quit())
        self.root.bind('<F5>', lambda e: self._start_scan())
        self.root.bind('<Delete>', lambda e: self._remove_selected_feed())
    
    def _setup_ui(self) -> None:
        """Construit l'interface utilisateur."""
        # ===== BARRE DE TITRE =====
        title_frame = tk.Frame(self.root, bg="#1A1A2E", height=40)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(title_frame, 
                              text=f"{APP_NAME} v{APP_VERSION}", 
                              font=("Segoe UI", 12, "bold"),
                              fg="white", 
                              bg="#1A1A2E")
        title_label.pack(side=tk.LEFT, padx=15, pady=8)
        
        # ===== CONTENEUR PRINCIPAL =====
        main_container = ttk.Frame(self.root, style="Main.TFrame")
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # ===== PANEL CONFIGURATION =====
        config_frame = ttk.LabelFrame(main_container, text=self.lang.get("label_api_key"), padding=10)
        config_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Ligne API Key
        api_frame = ttk.Frame(config_frame)
        api_frame.pack(fill=tk.X)
        
        ttk.Label(api_frame, text=self.lang.get("label_api_key")).pack(side=tk.LEFT, padx=(0, 10))
        
        self.api_var = tk.StringVar(value=self.config.get("api_key", ""))
        self.api_entry = ttk.Entry(api_frame, textvariable=self.api_var, width=60, show="•")
        self.api_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        self.save_btn = ttk.Button(api_frame, text=self.lang.get("btn_save"), command=self._save_api_key)
        self.save_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.test_btn = ttk.Button(api_frame, text=self.lang.get("btn_test"), command=self._test_api)
        self.test_btn.pack(side=tk.LEFT)
        
        # ===== PANEL CONTENU PRINCIPAL =====
        content_frame = ttk.Frame(main_container, style="Main.TFrame")
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # ---- Colonne Gauche : Flux RSS ----
        left_panel = ttk.Frame(content_frame, style="Main.TFrame")
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        feeds_frame = ttk.LabelFrame(left_panel, text=self.lang.get("label_feeds"), padding=10)
        feeds_frame.pack(fill=tk.BOTH, expand=True)
        
        # Liste des flux
        self.feeds_listbox = tk.Listbox(feeds_frame, height=12, width=40,
                                        font=("Segoe UI", 10),
                                        bg="white", 
                                        selectbackground="#0078D4",
                                        selectforeground="white")
        self.feeds_listbox.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Ajout de flux
        feed_add_frame = ttk.Frame(feeds_frame)
        feed_add_frame.pack(fill=tk.X)
        
        self.new_feed_var = tk.StringVar()
        self.new_feed_entry = ttk.Entry(feed_add_frame, textvariable=self.new_feed_var, width=33)
        self.new_feed_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        self.add_feed_btn = ttk.Button(feed_add_frame, text="+", width=3, command=self._add_feed)
        self.add_feed_btn.pack(side=tk.LEFT)
        
        self.remove_feed_btn = ttk.Button(feed_add_frame, text="×", width=3, command=self._remove_selected_feed)
        self.remove_feed_btn.pack(side=tk.LEFT, padx=(5, 0))
        
        # ---- Colonne Droite : Articles ----
        right_panel = ttk.Frame(content_frame, style="Main.TFrame")
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Barre d'outils
        toolbar = ttk.Frame(right_panel, style="Main.TFrame")
        toolbar.pack(fill=tk.X, pady=(0, 10))
        
        self.scan_btn = ttk.Button(toolbar, text=self.lang.get("btn_scan"), 
                                  command=self._start_scan, style="Accent.TButton")
        self.scan_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.export_btn = ttk.Button(toolbar, text=self.lang.get("btn_export"), command=self._export_articles)
        self.export_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.clear_btn = ttk.Button(toolbar, text=self.lang.get("btn_clear"), command=self._clear_articles)
        self.clear_btn.pack(side=tk.LEFT)
        
        # Recherche
        search_frame = ttk.Frame(right_panel, style="Main.TFrame")
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(search_frame, text=self.lang.get("label_search") + " :").pack(side=tk.LEFT)
        
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *a: self._filter_articles())
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=50)
        self.search_entry.pack(side=tk.LEFT, padx=(10, 0))
        
        # ---- Tableau des articles ----
        articles_frame = ttk.LabelFrame(right_panel, text=self.lang.get("label_articles"), padding=5)
        articles_frame.pack(fill=tk.BOTH, expand=True)
        
        # Treeview
        columns = ("title", "source", "date", "summary")
        self.tree = ttk.Treeview(articles_frame, columns=columns, show="tree headings")
        
        self.tree.heading("#0", text="")
        self.tree.heading("title", text=self.lang.get("column_title"))
        self.tree.heading("source", text=self.lang.get("column_source"))
        self.tree.heading("date", text=self.lang.get("column_date"))
        self.tree.heading("summary", text=self.lang.get("column_summary"))
        
        self.tree.column("#0", width=30, anchor="center")
        self.tree.column("title", width=300)
        self.tree.column("source", width=120)
        self.tree.column("date", width=100)
        self.tree.column("summary", width=500)
        
        # Scrollbars
        v_scroll = ttk.Scrollbar(articles_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scroll = ttk.Scrollbar(articles_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        
        articles_frame.grid_rowconfigure(0, weight=1)
        articles_frame.grid_columnconfigure(0, weight=1)
        
        # Double-clic
        self.tree.bind('<Double-1>', lambda e: self._open_article())
        
        # ===== BARRE D'ÉTAT =====
        status_frame = tk.Frame(self.root, bg="#F0F1F4", height=30)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        status_frame.pack_propagate(False)
        
        self.status_var = tk.StringVar(value=self.lang.get("status_ready"))
        self.status_label = tk.Label(status_frame, 
                                    textvariable=self.status_var,
                                    font=("Segoe UI", 9),
                                    bg="#F0F1F4",
                                    fg="#6B7280",
                                    anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        # Barre de progression
        self.progress = ttk.Progressbar(status_frame, mode='determinate', length=200)
        self.progress.pack(side=tk.RIGHT, padx=10)
        
        # ===== PANEL PARAMÈTRES =====
        settings_frame = ttk.LabelFrame(left_panel, text=self.lang.get("label_language"), padding=10)
        settings_frame.pack(fill=tk.X, pady=(10, 0))
        
        lang_frame = ttk.Frame(settings_frame)
        lang_frame.pack(fill=tk.X)
        
        self.lang_var = tk.StringVar(value=self.config.get_language())
        
        ttk.Radiobutton(lang_frame, text=self.lang.get("language_french"), 
                       variable=self.lang_var, value="fr",
                       command=self._change_language).pack(side=tk.LEFT, padx=5)
        
        ttk.Radiobutton(lang_frame, text=self.lang.get("language_english"), 
                       variable=self.lang_var, value="en",
                       command=self._change_language).pack(side=tk.LEFT, padx=5)
        
        # ---- Paramètre articles par flux ----
        max_frame = ttk.Frame(settings_frame)
        max_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(max_frame, text=self.lang.get("label_max_articles") + " :").pack(side=tk.LEFT)
        
        self.max_var = tk.IntVar(value=self.config.get_max_articles())
        self.max_spin = ttk.Spinbox(max_frame, from_=1, to=10, 
                                   textvariable=self.max_var,
                                   width=5,
                                   command=self._save_max_articles)
        self.max_spin.pack(side=tk.LEFT, padx=(5, 0))
    
    def _initialize_api(self) -> None:
        """Initialise l'API Groq avec la clé configurée."""
        api_key = self.config.get("api_key", "")
        if api_key:
            success = self.scanner.initialize_api(api_key)
            if success:
                self.status_var.set(self.lang.get("status_ready"))
                self.api_var.set(api_key)
            else:
                self.status_var.set(self.lang.get("error_api_key_missing"))
                self.api_var.set("")
                self.config.set("api_key", "")
    
    def _load_feeds(self) -> None:
        """Charge les flux RSS dans la liste."""
        self.feeds_listbox.delete(0, tk.END)
        for feed in self.config.get_feeds():
            if feed.get("enabled", True):
                self.feeds_listbox.insert(tk.END, feed.get("url", ""))
    
    def _save_api_key(self) -> None:
        """Sauvegarde la clé API."""
        api_key = self.api_var.get().strip()
        if api_key:
            success = self.scanner.initialize_api(api_key)
            if success:
                self.config.set("api_key", api_key)
                self.status_var.set(self.lang.get("message_api_saved"))
                messagebox.showinfo("Succès", self.lang.get("message_api_saved"))
            else:
                self.status_var.set(self.lang.get("message_api_error"))
                messagebox.showerror("Erreur", self.lang.get("message_api_error"))
        else:
            messagebox.showwarning("Attention", self.lang.get("error_api_key_missing"))
    
    def _test_api(self) -> None:
        """Teste la connexion à l'API."""
        api_key = self.api_var.get().strip()
        if not api_key:
            messagebox.showwarning("Attention", self.lang.get("error_api_key_missing"))
            return
        
        success = self.scanner.initialize_api(api_key)
        if success:
            messagebox.showinfo("Succès", self.lang.get("test_connection_success"))
            self.status_var.set(self.lang.get("test_connection_success"))
        else:
            messagebox.showerror("Erreur", self.lang.get("test_connection_failed"))
            self.status_var.set(self.lang.get("test_connection_failed"))
    
    def _add_feed(self) -> None:
        """Ajoute un flux RSS."""
        url = self.new_feed_var.get().strip()
        if url:
            self.config.add_feed(url)
            self._load_feeds()
            self.status_var.set(self.lang.get("message_feed_added"))
            self.new_feed_var.set("")
        else:
            messagebox.showwarning("Attention", self.lang.get("error_feed_invalid"))
    
    def _remove_selected_feed(self) -> None:
        """Supprime le flux RSS sélectionné."""
        selection = self.feeds_listbox.curselection()
        if selection:
            url = self.feeds_listbox.get(selection[0])
            self.config.remove_feed(url)
            self._load_feeds()
            self.status_var.set(self.lang.get("message_feed_removed"))
    
    def _change_language(self) -> None:
        """Change la langue de l'interface."""
        lang = self.lang_var.get()
        if lang != self.config.get_language():
            self.config.set_language(lang)
            self.lang.switch(lang)
            self.scanner.set_language(self.lang)
            
            # Mise à jour de l'interface
            self._update_ui_texts()
            
            messagebox.showinfo("Langue", self.lang.get("status_ready"))
    
    def _update_ui_texts(self) -> None:
        """Met à jour tous les textes de l'interface."""
        # Titre fenêtre
        self.root.title(self.lang.get("app_title"))
        
        # Labels des frames
        # TODO: Mettre à jour tous les labels (complexe, on le fera proprement)
        pass
    
    def _save_max_articles(self) -> None:
        """Sauvegarde le nombre max d'articles par flux."""
        self.config.set("max_articles_per_feed", self.max_var.get())
    
    def _start_scan(self) -> None:
        """Lance le scan des flux."""
        if self.scanner.is_running:
            return
        
        # Vérification de l'API
        api_key = self.config.get("api_key", "")
        if not api_key:
            messagebox.showwarning("Attention", self.lang.get("error_api_key_missing"))
            self.api_entry.focus()
            return
        
        if not self.scanner.client:
            success = self.scanner.initialize_api(api_key)
            if not success:
                messagebox.showerror("Erreur", self.lang.get("message_api_error"))
                return
        
        # Vérification des flux
        if self.feeds_listbox.size() == 0:
            messagebox.showwarning("Attention", self.lang.get("error_no_feeds"))
            return
        
        # Effacer les anciens articles de la vue (mais pas de la base)
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Désactiver le bouton
        self.scan_btn.config(state=tk.DISABLED)
        self.progress["value"] = 0
        self.status_var.set(self.lang.get("status_scanning"))
        
        # Lancer le scan
        threading.Thread(target=self.scanner.scan_all, daemon=True).start()
    
    def _on_scan_progress(self, value: float) -> None:
        """Callback de progression du scan."""
        self.root.after(0, lambda: self.progress.config(value=value))
    
    def _on_scan_status(self, message: str) -> None:
        """Callback de statut du scan."""
        self.root.after(0, lambda: self.status_var.set(message))
    
    def _on_article_found(self, article: Dict) -> None:
        """Callback quand un article est trouvé."""
        self.root.after(0, lambda: self._add_article_to_tree(article))
    
    def _on_scan_complete(self, total: int, new: int) -> None:
        """Callback de fin de scan."""
        self.root.after(0, lambda: self._scan_complete(total, new))
    
    def _add_article_to_tree(self, article: Dict) -> None:
        """Ajoute un article dans l'arbre."""
        # Vérification doublon
        for item in self.tree.get_children():
            if self.tree.item(item)["values"][3] == article.get("url", ""):
                return
        
        # Troncature du résumé pour l'affichage
        summary = article.get("summary", "")
        if len(summary) > 250:
            summary = summary[:247] + "..."
        
        self.tree.insert("", tk.END, text="●", values=(
            article.get("title", "")[:80],
            article.get("source", "")[:25],
            article.get("date", ""),
            summary
        ), tags=(article.get("url", ""),))
    
    def _scan_complete(self, total: int, new: int) -> None:
        """Finalise le scan."""
        self.scan_btn.config(state=tk.NORMAL)
        self.progress["value"] = 100
        self.status_var.set(self.lang.get("status_scan_done", count=new))
        
        if new > 0:
            messagebox.showinfo("Terminé", self.lang.get("status_scan_done", count=new))
    
    def _filter_articles(self) -> None:
        """Filtre les articles par recherche."""
        query = self.search_var.get().lower()
        for item in self.tree.get_children():
            values = self.tree.item(item)["values"]
            if not values:
                continue
            if query in values[0].lower() or query in values[3].lower():
                self.tree.reattach(item, "", tk.END)
            else:
                self.tree.detach(item)
    
    def _open_article(self) -> None:
        """Ouvre l'article sélectionné dans le navigateur."""
        selection = self.tree.selection()
        if selection:
            url = self.tree.item(selection[0])["tags"][0] if self.tree.item(selection[0])["tags"] else None
            if url:
                webbrowser.open(url)
    
    def _export_articles(self) -> None:
        """Exporte les articles affichés vers un fichier texte."""
        articles = []
        for item in self.tree.get_children():
            values = self.tree.item(item)["values"]
            if values:
                articles.append({
                    "title": values[0],
                    "source": values[1],
                    "date": values[2],
                    "summary": values[3]
                })
        
        if not articles:
            messagebox.showwarning("Attention", self.lang.get("message_no_articles"))
            return
        
        filename = f"veille_tech_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write("=" * 80 + "\n")
                f.write(f"VEILLE TECH PRO - {self.lang.get('app_title')}\n")
                f.write(f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}\n")
                f.write("=" * 80 + "\n\n")
                
                for i, article in enumerate(articles, 1):
                    f.write(f"[{i}] {article['title']}\n")
                    f.write(f"Source : {article['source']}\n")
                    f.write(f"Date   : {article['date']}\n")
                    f.write(f"\n📝 RÉSUMÉ :\n{article['summary']}\n")
                    f.write("-" * 80 + "\n\n")
            
            self.status_var.set(self.lang.get("message_export_done", filename=filename))
            messagebox.showinfo("Export", self.lang.get("message_export_done", filename=filename))
            
        except Exception as e:
            messagebox.showerror("Erreur", self.lang.get("error_unknown", error=str(e)))
    
    def _clear_articles(self) -> None:
        """Supprime tous les articles de la base."""
        if messagebox.askyesno("Confirmation", self.lang.get("btn_clear")):
            self.db.clear_articles()
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.status_var.set(self.lang.get("message_cleared"))
    
    def run(self) -> None:
        """Lance la boucle principale."""
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()
    
    def _on_close(self) -> None:
        """Gère la fermeture de l'application."""
        self.db.close()
        self.root.destroy()

# ============================================================================
# POINT D'ENTRÉE
# ============================================================================

def main() -> None:
    """Point d'entrée de l'application."""
    try:
        app = MainWindow()
        app.run()
    except Exception as e:
        print(f"Erreur fatale : {e}")
        import traceback
        traceback.print_exc()
        input("Appuyez sur Entrée pour quitter...")

if __name__ == "__main__":
    main()