# LLM-based Cooperative Editor

A web-based cooperative text editor using Streamlit and Huggingface Transformers, supporting free, paid, and super users with token-based text correction and collaboration.

## Features
- Free, paid, and super user roles
- Token-based text submission and correction
- Advanced grammar correction using T5 model (vennify/t5-base-grammar-correction)
- Blacklist management
- Collaboration and complaints system

## Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Initialize the database and import sample data:
   ```bash
   python init_db.py
   python import_data.py
   ```

3. Run the app:
   ```bash
   streamlit run app.py
   ```

## Sample Data
The application comes with sample data for testing:

### Users
- Super User: admin/admin123 (1000 tokens)
- Paid Users: 
  - paid_user1/123456 (200 tokens)
  - paid_user2/123456 (200 tokens)
- Free Users:
  - free_user1/123456 (20 tokens)
  - free_user2/123456 (20 tokens)

### Blacklist
Sample blacklisted words are included for testing the filtering system.

### Complaints
Sample complaints are included to demonstrate the complaint system functionality.

## User Roles
- **Free User**: Can submit up to 20 words with a 3-minute cooldown between submissions
- **Paid User**: Can submit unlimited text with token-based correction
- **Super User**: Can manage blacklist and handle user complaints

## Technical Details
- Uses SQLite for user and token management
- Implements grammar correction using Huggingface's T5 model fine-tuned for grammar correction
- Supports both automatic and self-correction modes
- Highlights exact changes made to the text
