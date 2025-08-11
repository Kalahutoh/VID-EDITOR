import os
import telebot
from moviepy.editor import VideoFileClip
import threading

# --- Configuration ---
# This securely gets the bot token from the Render environment.
BOT_TOKEN = os.environ.get('BOT_TOKEN')

# The number of seconds to trim from the start.
TRIM_SECONDS = 20

# Check if the token is available
if not BOT_TOKEN:
    print("FATAL ERROR: BOT_TOKEN environment variable not found.")
    # This helps in debugging if the bot fails to start on Render.
    # We exit so the server doesn't run without a token.
    exit()

bot = telebot.TeleBot(BOT_TOKEN)

# --- Bot Functions ---

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Handles the /start and /help commands."""
    bot.reply_to(message, 
        "Hello! I am the Lecture Trimmer Bot. 🚀\n\n"
        "Send me any video, and I will cut the first "
        f"{TRIM_SECONDS} seconds from it and send it back.\n\n"
        "Please note: Telegram bots have a 20MB file size limit for processing."
    )

def process_video_thread(message):
    """This function handles the entire video processing logic."""
    downloaded_file_path = None
    output_file_path = None

    try:
        # 1. Inform user and download video
        reply = bot.reply_to(message, "Video received! Preparing to process... ⏳")

        file_info = bot.get_file(message.video.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        downloaded_file_path = f"temp_{message.video.file_id}.mp4"
        with open(downloaded_file_path, 'wb') as new_file:
            new_file.write(downloaded_file)

        bot.edit_message_text("Download complete. Trimming the video... ✂️", chat_id=reply.chat.id, message_id=reply.message_id)

        # 2. Process video with moviepy
        with VideoFileClip(downloaded_file_path) as clip:
            if clip.duration <= TRIM_SECONDS:
                bot.edit_message_text(f"Video is too short to trim! It must be longer than {TRIM_SECONDS} seconds.", chat_id=reply.chat.id, message_id=reply.message_id)
                return # Stop processing

            # Create the trimmed clip
            trimmed_clip = clip.subclip(TRIM_SECONDS)
            output_file_path = f"trimmed_{message.video.file_id}.mp4"
            trimmed_clip.write_videofile(output_file_path, codec="libx264", audio_codec="aac")

        # 3. Upload the result
        bot.edit_message_text("Processing complete! Uploading... 🚀", chat_id=reply.chat.id, message_id=reply.message_id)

        with open(output_file_path, 'rb') as video_file:
            bot.send_video(message.chat.id, video_file, caption="Here is your trimmed video! ✨")

        bot.delete_message(chat_id=reply.chat.id, message_id=reply.message_id)

    except Exception as e:
        print(f"An error occurred: {e}")
        # Try to inform the user if something went wrong
        try:
            bot.reply_to(message, f"Oops! Something went wrong. Please try another video.\n\n(Error: {e})")
        except:
            pass # Fails silently if bot can't send message

    finally:
        # 4. Clean up all temporary files to save space
        if downloaded_file_path and os.path.exists(downloaded_file_path):
            os.remove(downloaded_file_path)
        if output_file_path and os.path.exists(output_file_path):
            os.remove(output_file_path)

@bot.message_handler(content_types=['video'])
def handle_video(message):
    """Receives a video and starts a new thread to process it."""
    # Using a thread means the bot can handle multiple requests without freezing
    processing_thread = threading.Thread(target=process_video_thread, args=(message,))
    processing_thread.start()

# --- Start The Bot ---
print("Bot is starting up...")
bot.polling(none_stop=True)

                                                                                            
