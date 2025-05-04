import logging
from sentence_transformers import SentenceTransformer, util

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def calculate_similarity(strings, target):
    """
    Calculate similarity scores between a list of strings and a target string.

    Args:
        strings (list of str): The list of strings to compare.
        target (str): The string to compare against.

    Returns:
        list of dict: A list of dictionaries containing the string and its similarity score.
        This list is sorted by highest similarity and a part of the contract.
    """
    # Load the pretrained model
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # Compute embeddings
    target_embedding = model.encode(target, convert_to_tensor=True)
    string_embeddings = model.encode(strings, convert_to_tensor=True)

    # Compute cosine similarity
    similarities = util.cos_sim(target_embedding, string_embeddings)[0]

    results = []
    for string, score in zip(strings, similarities.tolist()):
        results.append({'value': string, 'similarity_score': score})
        logger.debug(f'String: {string}, Similarity Score: {score:.2f}')

    # Sort results by similarity score in descending order
    results.sort(key=lambda x: x['similarity_score'], reverse=True)
    return results

if __name__ == "__main__":
    # Example usage
    strings = [    "infosec", "Account Issues", "Technical Support", "Security", "Team Collaboration"]
    target = "IT"
    results = calculate_similarity(strings, target)
    for result in results:
        print(f"String: {result['value']}, Similarity Score: {result['similarity_score']:.2f}")

