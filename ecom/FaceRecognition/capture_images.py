import cv2
import os

def capture_images_for_user(username, count=5):
    cap = cv2.VideoCapture(0)
    output_dir = os.path.join("dataset", username)
    os.makedirs(output_dir, exist_ok=True)
    captured = 0

    print(f"Capturing {count} images for '{username}'... Press 's' to save. Press 'q' to quit.")

    while captured < count:
        ret, frame = cap.read()
        
        if not ret:
            break
        
        cv2.imshow("Capture Images", frame)

        key = cv2.waitKey(1)
        # print(ord('s') , key&0xFF)
        if key & 0xFF == ord('s'):
            img_path = os.path.join(output_dir, f"{captured + 1}.jpg")
            cv2.imwrite(img_path, frame)
            print(f"Saved: {img_path}")
            captured += 1

        elif key & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    
def save_frame(frame , userid , count):
    OUTPUT_DIR = "C:\\Users\\A S\\OneDrive\\Desktop\\Online_Shopping_Project_Django_Development\\ecom\\FaceRecognition\\dataset"
    output_dir = os.path.join(OUTPUT_DIR, str(userid))
    os.makedirs(output_dir, exist_ok=True)
    img_path = os.path.join(output_dir, f"{count + 1}.jpg")
    cv2.imwrite(img_path , frame)
    print(f"Saved: {img_path}")

if __name__ == "__main__":
    name = input("Enter username: ")
    capture_images_for_user(name, count=5)
