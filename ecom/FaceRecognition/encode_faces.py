import face_recognition
import os
import pickle
import multiprocessing
from functools import partial
import cv2
import hashlib
import json
import time
from collections import Counter

DATASET_DIR = "C:\\Users\\A S\\OneDrive\\Desktop\\Online_Shopping_Project_Django_Development\\ecom\\FaceRecognition\\dataset"
ENCODING_FILE = "C:\\Users\\A S\\OneDrive\\Desktop\\Online_Shopping_Project_Django_Development\\ecom\\FaceRecognition\\encodings\\known_faces.pkl"
CACHE_FILE = "C:\\Users\\A S\\OneDrive\\Desktop\\Online_Shopping_Project_Django_Development\\ecom\\FaceRecognition\\encodings\\cache.json"
MAX_SIZE = 640  # Maximum dimension for resizing

def get_image_hash(image_path):
    """Generate a hash based on file path and modification time"""
    mod_time = os.path.getmtime(image_path)
    return hashlib.md5(f"{image_path}_{mod_time}".encode()).hexdigest()

def load_cache():
    """Load the processing cache if it exists"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_cache(cache):
    """Save the processing cache"""
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f)

def process_image(image_path, person_name, cache):
    """Process a single image and return its encoding"""
    # Checking if image is in cache
    image_hash = get_image_hash(image_path)
    if image_hash in cache:
        print(f"Using cached encoding for: {image_path}")
        return cache[image_hash], person_name, "cached", image_hash

    print(f"Processing new image: {image_path}")
    try:
        # Read image with OpenCV and resizing it
        image = cv2.imread(image_path)
        if image is None:
            print(f"Could not read image: {image_path}")
            return None, None, "failed_read", image_hash

        # Resize if image is large
        h, w = image.shape[:2]
        resized = False
        if max(h, w) > MAX_SIZE:
            scale = MAX_SIZE / max(h, w)
            image = cv2.resize(image, (int(w * scale), int(h * scale)))
            resized = True

        # Converting from BGR to RGB
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Detecting faces using HOG model
        face_locations = face_recognition.face_locations(rgb_image, model="hog")

        if not face_locations:
            print(f"No face found in {os.path.basename(image_path)}")
            return None, None, "no_face", image_hash

        # Get face encodings
        encodings = face_recognition.face_encodings(rgb_image, face_locations)
        if encodings:
            # Returning encoding and hash for caching.
            status = "success_resized" if resized else "success"
            return encodings[0], person_name, status, image_hash
    except Exception as e:
        print(f"Error processing {image_path}: {e}")

    return None, None, "error", image_hash

def encode_faces():
    start_time = time.time()
    
    # Loading cache
    cache = load_cache()
    old_cache_size = len(cache)
    
    # Initializing statistics (for debugging the face encoding process)
    stats = Counter({
        'total': 0,
        'cached': 0,
        'new': 0,
        'success': 0,
        'no_face': 0,
        'failed_read': 0,
        'error': 0,
        'resized': 0
    })
    
    # Collecting all image paths
    image_data = []
    person_counts = Counter()
    
    for person_name in os.listdir(DATASET_DIR):
        person_folder = os.path.join(DATASET_DIR, person_name)
        
        if not os.path.isdir(person_folder):
            continue
        
        person_images = 0
        for image_name in os.listdir(person_folder):
            image_path = os.path.join(person_folder, image_name)
            image_data.append((image_path, person_name))
            person_images += 1
            stats['total'] += 1
        
        person_counts[person_name] = person_images
    
    print(f"\n{'='*60}")
    print(f"FACE ENCODING PROCESS STARTED")
    print(f"{'='*60}")
    print(f"Total images to process: {stats['total']}")
    print(f"Images in cache: {old_cache_size}")
    print(f"People in dataset: {len(person_counts)}")
    for person, count in person_counts.items():
        print(f"  - {person}: {count} images")
    
    # Processing multiple images in parallel
    num_processes = max(1, multiprocessing.cpu_count() - 1)  # Leaving one cpu for other os process
    print(f"\nUsing {num_processes} processes for encoding")

    known_encodings = []
    known_names = []

    # Use multiprocessing module for parallel processing
    with multiprocessing.Pool(processes=num_processes) as pool:
        process_func = partial(process_image, cache=cache)
        results = pool.starmap(process_func, image_data)

    # Filtering out None results (already in cache) and collect statistics
    result_stats = Counter()
    for encoding, name, status, image_hash in results:
        result_stats[status] += 1

        # Updating cache with new encodings
        if encoding is not None and status.startswith("success"):
            cache[image_hash] = encoding.tolist()

        if encoding is not None:
            # Converting the list back to numpy array if its not from cache
            if isinstance(encoding, list):
                import numpy as np
                encoding = np.array(encoding)
            known_encodings.append(encoding)
            known_names.append(name)

    # Updating stats based on results
    stats['cached'] = result_stats['cached']
    stats['success'] = result_stats['success'] + result_stats.get('success_resized', 0)
    stats['no_face'] = result_stats['no_face']
    stats['failed_read'] = result_stats['failed_read']
    stats['error'] = result_stats['error']
    stats['resized'] = result_stats.get('success_resized', 0)
    
    # Saving encodings
    os.makedirs("encodings", exist_ok=True)
    with open(ENCODING_FILE, 'wb') as f:
        pickle.dump((known_encodings, known_names), f)
    
    # Saving updated cache
    new_cache_size = len(cache)
    cache_added = new_cache_size - old_cache_size
    save_cache(cache)
    
    elapsed_time = time.time() - start_time
    
    # print(f"\n{'='*60}")
    # print(f"FACE ENCODING PROCESS COMPLETED")
    # print(f"{'='*60}")
    # print(f"Total processing time: {elapsed_time:.2f} seconds")
    # print(f"Images processed: {stats['total']}")
    # print(f"  - Previously cached: {stats['cached']} ({stats['cached']/stats['total']*100:.1f}%)")
    # print(f"  - Newly processed: {stats['total'] - stats['cached']} ({(stats['total'] - stats['cached'])/stats['total']*100:.1f}%)")
    # print(f"  - Successfully encoded: {stats['success']} ({stats['success']/stats['total']*100:.1f}%)")
    # print(f"  - No face detected: {stats['no_face']} ({stats['no_face']/stats['total']*100:.1f}%)")
    # print(f"  - Failed to read: {stats['failed_read']} ({stats['failed_read']/stats['total']*100:.1f}%)")
    # print(f"  - Error during processing: {stats['error']} ({stats['error']/stats['total']*100:.1f}%)")
    # print(f"  - Resized for processing: {stats['resized']} ({stats['resized']/stats['total']*100:.1f}%)")
    # print(f"\nCache statistics:")
    # print(f"  - Previous cache size: {old_cache_size}")
    # print(f"  - New cache size: {new_cache_size}")
    # print(f"  - New entries added: {cache_added}")
    # print(f"\nFinal results:")
    # print(f"  - Total face encodings saved: {len(known_encodings)}")
    
    # printing per-person statistics
    person_success = Counter()
    for name in known_names:
        person_success[name] += 1
    
    print(f"\nPer-person success rate:")
    for person, total in person_counts.items():
        success = person_success[person]
        print(f"  - {person}: {success}/{total} successful ({success/total*100:.1f}%)")
    
    print(f"\nFace encodings saved to: {os.path.abspath(ENCODING_FILE)}")
    print(f"{'='*60}")

if __name__ == "__main__":
    encode_faces()
