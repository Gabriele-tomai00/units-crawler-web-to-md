set -e

ENV_DIR="env"
REQUIREMENTS_FILE="requirements.txt"

# --- Default depth limit ---
DEPTH_LIMIT=4

# --- Parse arguments ---
while [[ $# -gt 0 ]]; do
    case "$1" in
        --depth|-d)
            DEPTH_LIMIT="$2"
            shift 2
            ;;
        *)
            printf "Unknown parameter: $1\n"
            exit 1
            ;;
    esac
done

printf "Using DEPTH_LIMIT = $DEPTH_LIMIT \n"

# --- Check/Create Virtual Environment ---
EXPECTED_ENV="$PWD/$ENV_DIR"

if [[ ! -d "$ENV_DIR" ]]; then
    printf "Virtual environment not found. Creating it in '$ENV_DIR'...\n"
    python3 -m venv "$ENV_DIR"
    source "$ENV_DIR/bin/activate"
    if [[ -f "$REQUIREMENTS_FILE" ]]; then
        pip install --upgrade pip
        pip install -r "$REQUIREMENTS_FILE"
    else
        printf "WARNING: requirements.txt not found. Continuing without installing packages.\n"
    fi
else
    # Activate if not active, or if a different env is active
    if [[ "$VIRTUAL_ENV" != "$EXPECTED_ENV" ]]; then
        printf "Activating virtual environment...\n"
        source "$ENV_DIR/bin/activate"
    else
        printf "Virtual environment already active: $VIRTUAL_ENV\n"
    fi

    # Always sync requirements in case requirements.txt has changed
    if [[ -f "$REQUIREMENTS_FILE" ]]; then
        printf "Syncing requirements...\n"
        pip install -q -r "$REQUIREMENTS_FILE"
    fi
fi

export PATH="$EXPECTED_ENV/bin:$PATH"
printf "Using Python: $(which python3)\n"  # debug: confirm correct python


# --- Delete old results ---
printf "Delete old results\n"
mkdir -p results_scrapy
cd results_scrapy
rm -rf scraper_results_${DEPTH_LIMIT} filtered_items_${DEPTH_LIMIT}.jsonl summary_domains_numbers_${DEPTH_LIMIT}.txt links_list_${DEPTH_LIMIT}.txt
cd ..


# --- Scraping part ---
printf "\nRun scraper\n"
cd units_crawler
scrapy crawl units_global_crawler -s DEPTH_LIMIT=$DEPTH_LIMIT -s ROTARY_USER_AGENT=True -a output_dir="../results_scrapy/scraper_results_${DEPTH_LIMIT}"
cd ..

# --- Domain numbers ---
printf "\nRun domains_numbers.py\n"
python3 scripts/domains_numbers.py -d $DEPTH_LIMIT --dir "results_scrapy/"
# python3 scripts/domains_numbers.py -d 1 --dir "results_scrapy/"

# --- Cleaning part ---
printf "\nRun pages_cleaner.py\n"
python3 scripts/pages_cleaner.py \
    --input "results_scrapy/scraper_results_${DEPTH_LIMIT}/" \
    --output "results_scrapy/filtered_items_${DEPTH_LIMIT}.jsonl" \
# 
# python3 scripts/pages_cleaner.py \
#     --input "results_scrapy/scraper_results_1/" \
#     --output "results_scrapy/filtered_items_1.jsonl" \
