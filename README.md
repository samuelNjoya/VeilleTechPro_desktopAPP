# Veille Tech Pro

**Assistant de veille technologique avec résumé par IA**

---

## 🎯 Description

Veille Tech Pro est une application desktop Windows qui vous permet de :

- 📡 **Suivre** vos flux RSS préférés (technologie, sciences, actualités)
- 🤖 **Résumer** automatiquement les articles par IA (Groq)
- 🌍 **Choisir** la langue des résumés (Français / English)
- 💾 **Conserver** un historique des articles lus
- 🔍 **Rechercher** dans vos résumés
- 📤 **Exporter** vos résumés en fichier texte

---

## 🚀 Installation

### Prérequis

- Python 3.10 ou supérieur
- Clé API Groq (gratuite) : [console.groq.com](https://console.groq.com)

### Installation depuis les sources

```bash
# 1. Cloner le projet
git clone https://github.com/veilletech/VeilleTechPro.git
cd VeilleTechPro

# 2. Créer l'environnement virtuel
python -m venv venv
source venv/bin/activate  # Windows : venv\Scripts\activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configurer la clé API
cp .env.example .env
# Modifier .env avec votre clé

# 5. Lancer l'application
python veille_tech_pro.py

# Créer l'environnement virtuel
python -m venv venv

# Activer l'environnement
# - Sur Windows :
venv\Scripts\activate

# - Sur Linux/Mac :
source venv/bin/activate


pip install groq feedparser beautifulsoup4 requests python-dotenv

custumTkenter: pour les app modernes pip install customtkinter r