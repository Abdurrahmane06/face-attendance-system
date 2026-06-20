#!/bin/bash
# ======================================================================
# run_pgtap.sh — Installe pgTAP et exécute les tests sur la base
# ======================================================================
# Utilisation :
#   ./data_base/run_pgtap.sh             # utilise les valeurs par défaut
#   ./data_base/run_pgtap.sh -d ma_base  # base personnalisée
#   ./data_base/run_pgtap.sh -H hôte     # hôte personnalisé
# ======================================================================

set -euo pipefail

DB_NAME="${POSTGRES_DB:-faceattend}"
DB_USER="${POSTGRES_USER:-faceattend}"
DB_PASS="${POSTGRES_PASSWORD:-password}"
DB_HOST="${PGHOST:-localhost}"
DB_PORT="${PGPORT:-5432}"
PGTAP_VERSION="1.3.3"

usage() {
    echo "Usage: $0 [-d db_name] [-U user] [-H host] [-p port] [-h]"
    exit 1
}

while getopts "d:U:H:p:h" opt; do
    case $opt in
        d) DB_NAME="$OPTARG" ;;
        U) DB_USER="$OPTARG" ;;
        H) DB_HOST="$OPTARG" ;;
        p) DB_PORT="$OPTARG" ;;
        h) usage ;;
        *) usage ;;
    esac
done

export PGPASSWORD="$DB_PASS"

echo "========================================="
echo "  Installation de pgTAP v${PGTAP_VERSION}"
echo "========================================="

# Vérifier si pgTAP est déjà installé
if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc \
    "SELECT EXISTS(SELECT 1 FROM pg_available_extensions WHERE name='pgtap');" 2>/dev/null | grep -q 't'; then
    echo "✓ pgTAP est déjà disponible sur le serveur"
else
    echo "→ pgTAP n'est pas installé sur le serveur."
    echo "  Pour l'installer dans le conteneur Docker :"
    echo ""
    echo "  docker exec faceattend-db bash -c \""
    echo "    apt-get update && \\"
    echo "    apt-get install -y postgresql-15-pgtap && \\"
    echo "    psql -U $DB_USER -d $DB_NAME -c 'CREATE EXTENSION IF NOT EXISTS pgtap;'"
    echo "  \""
    echo ""
    echo "  Ou ajoutez ce Dockerfile pour le service postgres :"
    echo ""
    echo "  # postgres/Dockerfile"
    echo "  FROM postgres:15"
    echo "  RUN apt-get update && apt-get install -y postgresql-15-pgtap"
    echo ""

    read -rp "Voulez-vous tenter l'installation automatique dans le conteneur ? (y/N) " answer
    if [[ "$answer" =~ ^[Yy]$ ]]; then
        echo "→ Installation de pgTAP dans le conteneur faceattend-db..."
        docker exec faceattend-db bash -c "
            apt-get update -qq && \
            apt-get install -y -qq postgresql-15-pgtap 2>/dev/null && \
            psql -U $DB_USER -d $DB_NAME -c 'CREATE EXTENSION IF NOT EXISTS pgtap;'
        " || {
            echo "✗ Échec de l'installation automatique."
            exit 1
        }
        echo "✓ pgTAP installé avec succès"
    else
        echo "Installation annulée. Installez pgTAP manuellement puis relancez."
        exit 1
    fi
fi

echo ""
echo "========================================="
echo "  Initialisation de la base de données"
echo "========================================="
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$(dirname "$0")/init.sql"
echo "✓ Base initialisée"

echo ""
echo "========================================="
echo "  Exécution des tests pgTAP"
echo "========================================="
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$(dirname "$0")/test_schema.pg"

echo ""
echo "========================================="
echo "  Terminé"
echo "========================================="
