import cv2
import face_recognition
import pickle
import os

# Get the directory where this script is located
current_dir = os.path.dirname(os.path.abspath(__file__))
ENCODING_FILE = os.path.join(current_dir, "encodings", "known_faces.pkl")

def load_known_faces():
    with open(ENCODING_FILE, "rb") as f:
        return pickle.load(f)

def live_face_recognition(image):
    known_encodings, known_users = load_known_faces()

    # cap = cv2.VideoCapture(0)
    print("Live face recognition started. Press 'q' to quit.")

    frame = image

    small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
    #cv2.imshow('scale down' , small_frame)
    rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

    face_locations = face_recognition.face_locations(rgb_small_frame)
    face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

    for face_encoding, face_location in zip(face_encodings, face_locations):
        matches = face_recognition.compare_faces(known_encodings, face_encoding)
        face_distances = face_recognition.face_distance(known_encodings, face_encoding)
        name = "Unknown"

        if matches:
            best_match_index = face_distances.argmin()
            if matches[best_match_index]:
                name = known_users[best_match_index]

        top, right, bottom, left = [v * 4 for v in face_location]
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
        cv2.rectangle(frame, (left, bottom - 30), (right, bottom), (0, 255, 0), cv2.FILLED)
        cv2.putText(frame, name, (left + 6, bottom - 6),
                    cv2.FONT_HERSHEY_DUPLEX, 0.9, (0, 0, 0), 1)
    
    # cv2.imshow("Live Face Recognition", frame)

    cv2.destroyAllWindows()
    
    return (frame , name)

if __name__ == "__main__":
    live_face_recognition()
