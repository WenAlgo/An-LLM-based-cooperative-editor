from transformers import pipeline, AutoModelForSeq2SeqLM, AutoTokenizer
from blacklist import get_blacklist, is_blacklisted
import re

def load_llm():
    """Load a grammar correction model"""
    try:
        # Use T5 model specifically fine-tuned for grammar correction
        model = AutoModelForSeq2SeqLM.from_pretrained('vennify/t5-base-grammar-correction')
        tokenizer = AutoTokenizer.from_pretrained('vennify/t5-base-grammar-correction')
        return pipeline('text2text-generation', 
                       model=model, 
                       tokenizer=tokenizer,
                       max_length=128,
                       num_beams=5,
                       early_stopping=True)
    except Exception as e:
        print(f"Error loading model: {e}")
        return None

def preprocess_text(text: str) -> str:
    """Preprocess text for grammar correction"""
    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text.strip())
    # Ensure proper sentence ending
    if not text.endswith(('.', '!', '?')):
        text += '.'
    return text

def correct_text(llm, text: str) -> str:
    """Correct grammar in text using the LLM"""
    if not llm:
        return text
    
    try:
        # Preprocess the input text
        text = preprocess_text(text)
        
        # Split text into sentences
        sentences = text.split('.')
        corrected_sentences = []
        
        for sentence in sentences:
            if not sentence.strip():
                continue
                
            # Add period back for processing
            sentence = sentence.strip() + '.'
            
            # Generate correction with optimized parameters
            result = llm(f"grammar: {sentence}", max_length=128, num_beams=5, early_stopping=True)
            corrected = result[0]['generated_text']
            
            # Remove the "grammar: " prefix if present
            if corrected.startswith("grammar: "):
                corrected = corrected[9:]
                
            corrected_sentences.append(corrected)
        
        # Join sentences back together
        return ' '.join(corrected_sentences)
    except Exception as e:
        print(f"Error correcting text: {e}")
        return text

def mask_blacklisted_words(text):
    words = text.split()
    masked_words = []
    
    for word in words:
        if is_blacklisted(word):
            masked_words.append('*' * len(word))
        else:
            masked_words.append(word)
    
    return ' '.join(masked_words)

def highlight_corrections(original: str, corrected: str) -> str:
    """Highlight differences between original and corrected text"""
    original_words = original.split()
    corrected_words = corrected.split()
    
    result = []
    i = j = 0
    while i < len(original_words) or j < len(corrected_words):
        if i < len(original_words) and j < len(corrected_words) and original_words[i] == corrected_words[j]:
            result.append(original_words[i])
            i += 1
            j += 1
        else:
            if j < len(corrected_words):
                result.append(f"**{corrected_words[j]}**")
                j += 1
            if i < len(original_words):
                i += 1
    
    return " ".join(result) 