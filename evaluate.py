import os
import pandas as pd
import numpy as np
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from nltk.metrics import edit_distance
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import scipy.stats
from collections import Counter
import math


def levenshtein_similarity(a, b):
    """Calculate Levenshtein similarity between two strings"""
    return 1 - (edit_distance(a, b) / max(len(a), len(b)))


def jaccard_similarity(a, b):
    """Calculate Jaccard similarity between two sets of tokens"""
    a_tokens = set(a.split())
    b_tokens = set(b.split())
    intersection = a_tokens.intersection(b_tokens)
    union = a_tokens.union(b_tokens)
    return len(intersection) / len(union)


def kl_divergence(a, b):
    """Calculate KL divergence between two probability distributions"""
    a_counts = pd.Series(a).value_counts(normalize=True)
    b_counts = pd.Series(b).value_counts(normalize=True)
    a_probs = a_counts / a_counts.sum()
    b_probs = b_counts / b_counts.sum()
    return scipy.stats.entropy(a_probs, b_probs)


def euclidean_distance(a,b):
    vector1 = Counter(a)
    vector2 = Counter(b)

    # Combine all unique words from both sets
    all_words = set(vector1) | set(vector2)

    # Compute Euclidean distance
    distance = math.sqrt(sum((vector1[word] - vector2[word])**2 for word in all_words))
    return distance


tokenizer = AutoTokenizer.from_pretrained("mistralai/Mistral-7B-Instruct-v0.2")
llm_generator = pipeline('text-generation', model='mistralai/Mistral-7B-Instruct-v0.2', tokenizer = tokenizer, trust_remote_code=True)

metadata_df = pd.read_csv('metadata.csv')


def generate_prompt(text, length_factor, operation):
    target_length = int(len(text.split()) * length_factor) if operation == 'longer' else int(len(text.split()) / length_factor)
    return (target_length, f"Generate an essay that is {length_factor * 100 if operation == 'longer' else 100 / length_factor}% the length of this in the same style:\n\n{text}")


# Initialize empty lists to store results
results = []

# Main evaluation loop
for _, row in metadata_df.iterrows():
    file_name = row['file_name']
    original_text = row['original-text']
    original_length = int(len(original_text.split()))

    # for length_factor in [0.25, 0.5, 0.75, 1.0]:
    for length_factor in [0.25, 0.5, 0.75]:
        for operation in ['longer', 'shorter']:
            tar_len, prompt = generate_prompt(original_text, length_factor, operation)
            print(prompt)
            print(original_length)

            generated_text = llm_generator(prompt, max_length=tar_len, truncation=True)[0]['generated_text']
            print(generated_text)


            # Calculate evaluation metrics
            levenshtein_sim = levenshtein_similarity(original_text, generated_text)
            jaccard_sim = jaccard_similarity(original_text, generated_text)
            vectorizer = TfidfVectorizer()
            original_vectors = vectorizer.fit_transform([original_text])
            generated_vectors = vectorizer.transform([generated_text])
            cosine_sim = cosine_similarity(original_vectors, generated_vectors)[0][0]
            kl_div = kl_divergence(original_text.split(), generated_text.split())
            euclidean_dist = euclidean_distance(original_text.split(), generated_text.split())

            # Store results
            results.append({
                'file_name': file_name,
                'original_length': original_length,
                'length_factor': length_factor,
                'operation': operation,
                'model': 'gpt3',
                'generated_text': generated_text,
                'generated_length': len(generated_text.split()),
                'levenshtein_similarity': levenshtein_sim,
                'jaccard_similarity': jaccard_sim,
                'cosine_similarity': cosine_sim,
                'kl_divergence': kl_div,
                'euclidean_distance': euclidean_dist
            })

# Create a DataFrame from the results
results_df = pd.DataFrame(results)

# Save the results to a CSV file
results_df.to_csv('evaluation_results.csv', index=False)

print('Evaluation results saved to evaluation_results.csv')
