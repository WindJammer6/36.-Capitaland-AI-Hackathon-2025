import gradio as gr
import logging
import re
import os
from pathlib import Path
import html
from urllib.parse import unquote
from thefuzz import process

logger = logging.getLogger(__name__)

def scan_files_directory(files_directory="public/files/"):
    """Scan the files directory and return file information for fuzzy matching"""
    try:
        # Get absolute path to the files directory
        files_dir = Path(files_directory)
        
        # Get all files in the directory recursively
        if not files_dir.exists():
            logger.warning(f"Files directory {files_directory} does not exist")
            return None
            
        all_files = []
        for file_path in files_dir.rglob("*"):
            if file_path.is_file():
                # Store both the relative path and filename without extension for matching
                relative_path = file_path.relative_to(Path("."))
                filename_without_ext = file_path.stem
                all_files.append({
                    'path': str(relative_path),
                    'name_without_ext': filename_without_ext,
                    'full_name': file_path.name
                })
        
        if not all_files:
            logger.info(f"No files found in {files_directory}")
            return None
        
        return all_files
            
    except Exception as e:
        logger.error(f"Error scanning files directory: {e}")
        return None

def find_best_match(filename, file_list):
    """Find the best matching file from a pre-scanned file list using fuzzy matching"""
    try:
        if not file_list:
            return None
        
        # Remove extension from the target filename for comparison
        target_name = Path(filename).stem
        
        # Create list of names without extensions for fuzzy matching
        names_for_matching = [f['name_without_ext'] for f in file_list]
        
        # Find the best match using fuzzy matching
        best_match = process.extractOne(target_name, names_for_matching)
        
        if best_match and best_match[1] > 60:  # Threshold of 60% similarity
            # Find the corresponding file info
            matched_index = names_for_matching.index(best_match[0])
            matched_file = file_list[matched_index]
            logger.info(f"Found fuzzy match for '{filename}': {matched_file['path']} (score: {best_match[1]})")
            return matched_file['path']
        else:
            logger.info(f"No good fuzzy match found for '{filename}' (best score: {best_match[1] if best_match else 'N/A'})")
            return None
            
    except Exception as e:
        logger.error(f"Error in fuzzy file matching: {e}")
        return None

def find_closest_file(filename, files_directory="public/files/"):
    """Find the closest matching file in the files directory using fuzzy matching (legacy function)"""
    file_list = scan_files_directory(files_directory)
    return find_best_match(filename, file_list)

def extract_markdown_links(text):
    """Extract markdown links from text and return filename-link pairs"""
    # Regex pattern for markdown links: [text](url)
    pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    matches = re.findall(pattern, text)
    
    if not matches:
        return []
    
    # Scan files directory once for all links
    file_list = scan_files_directory()
    
    links_info = []
    for link_text, url in matches:
        # Skip http/https links
        if url.startswith("http://") or url.startswith("https://"):
            continue

        # Extract filename from URL or use link text
        filename = Path(url).name if url else link_text
        # If no filename extension found, use the link text as filename
        if not filename or '.' not in filename:
            filename = link_text
        
        # Decode percent-encoded characters in filename (like %20 -> space)
        filename = unquote(filename)
        
        # Try to find a matching file using the pre-scanned file list
        matched_filepath = find_best_match(filename, file_list)
        
        # Use the matched filepath if found, otherwise keep the original URL
        final_url = f"/gradio_api/file={matched_filepath}" if matched_filepath else url
        
        links_info.append({
            'filename': filename.split('.')[0],
            'url': final_url,
            'original_link': f"[{link_text}]({url})",
            'text': link_text,
            'fuzzy_matched': matched_filepath is not None
        })
    
    return links_info

def user(user_message, history):
    """Add user message to history immediately"""
    return "", history + [{"role": "user", "content": user_message}]

async def bot(history):
    """Stream bot response using async Azure client"""
    user_message = history[-1]["content"]
    
    # Add empty assistant message to history
    history.append({"role": "assistant", "content": ""})
    
    try:
        logger.info(f"Sending message to Azure agent: {user_message}")
        
        # Use the async streaming function directly
        from src.azure import send_message_to_agent_streaming
        
        # Stream the response from Azure
        async for chunk in send_message_to_agent_streaming(user_message):
            history[-1]["content"] += chunk
            yield history
        
        # After streaming is complete, check for markdown links
        final_message = history[-1]["content"]
        links_info = extract_markdown_links(final_message)
        
        if links_info:
            logger.info(f"Found {len(links_info)} links to process")
            
            # Replace original markdown links with anchor links
            updated_message = final_message
            for i, link_info in enumerate(links_info):
                # Create unique anchor ID for each card
                anchor_id = f"source-card-{i}"
                # Replace the markdown link with an anchor link that scrolls to the card
                original_link = link_info['original_link']
                anchor_link = f'<a href="#{anchor_id}" onclick="document.getElementById(\'{anchor_id}\').scrollIntoView({{behavior: \'smooth\'}}); return false;">{html.escape(link_info["text"])}</a>'
                updated_message = updated_message.replace(original_link, anchor_link, 1)
                logger.info(f"Replaced link {i}: {original_link}")
            
            # Create individual source cards HTML - build as one complete string
            cards_components = []
            for i, link_info in enumerate(links_info):
                # Escape HTML content to prevent malformed display
                escaped_filename = html.escape(link_info['filename'])
                escaped_url = html.escape(link_info['url'])
                anchor_id = f"source-card-{i}"
                
                card_html = f'<div class="source-card" id="{anchor_id}"><div class="card-icon">📄</div><div class="card-title">{escaped_filename}</div><a href="{escaped_url}" class="card-link" target="_blank">Download</a></div>'
                cards_components.append(card_html)
                logger.info(f"Created card {i}: {escaped_filename}")
            
            # Join all cards into the container
            cards_html = f'\n\n<div class="source-cards-container">{"".join(cards_components)}</div>'
            logger.info(f"Final cards HTML length: {len(cards_html)}")
            
            # Update the message content with replaced links and append source cards
            history[-1]["content"] = updated_message + cards_html
            yield history
        
    except Exception as e:
        logger.error(f"Error communicating with Azure agent: {e}")
        error_msg = "Sorry, I encountered an error while processing your request. Please try again."
        history[-1]["content"] = error_msg
        yield history

gr.set_static_paths(paths=["public/files/"])

with gr.Blocks(css="""
/* Source cards container */
.source-cards-container {
    display: flex;
    overflow-x: auto;
    gap: 0.5rem;
    padding: 0.5rem 0;
    margin-top: 0.75rem;
}
.source-card {
    border: 1px solid var(--border-color-primary, #e5e7eb);
    border-radius: var(--radius-md, 0.375rem);
    padding: 0.75rem;
    min-width: 10rem;
    max-width: 13.75rem;
    flex-shrink: 0;
    text-align: center;
    background: var(--background-fill-secondary, transparent);
    transition: all 0.15s ease;
    scroll-margin-top: 1.25rem;
    display: flex;
    flex-direction: column;
}
.source-card:hover {
    border-color: var(--border-color-accent, #9ca3af);
    transform: translateY(-0.0625rem);
}
.source-card:target {
    border-color: var(--link-text-color, #3b82f6);
    box-shadow: 0 0 0 0.125rem var(--link-text-color, #3b82f6);
    animation: highlight 1s ease-out;
}
@keyframes highlight {
    0% { background-color: var(--link-text-color-light, #eff6ff); }
    100% { background-color: transparent; }
}
.card-icon {
    font-size: 1.125rem;
    margin-bottom: 0.375rem;
    opacity: 0.7;
}
.card-title {
    font-weight: 500;
    margin-bottom: 0.5rem;
    font-size: 0.8125rem;
    color: var(--body-text-color, inherit);
    word-break: break-word;
    line-height: 1.3;
}
.card-link {
    display: inline-block;
    color: var(--link-text-color, #3b82f6) !important;
    text-decoration: none;
    padding: 0.25rem 0.5rem;
    border-radius: var(--radius-sm, 0.25rem);
    font-size: 0.6875rem;
    margin-top: auto;
    border: 1px solid var(--link-text-color, #3b82f6);
    transition: all 0.15s ease;
    background: transparent;
}
.card-link:hover {
    background: var(--link-text-color, #3b82f6);
    color: white !important;
    text-decoration: none;
}
/* Styles for anchor links in chat messages */
.chatbot a[href^="#source-card-"] {
    color: var(--link-text-color, #3b82f6) !important;
    text-decoration: underline;
    cursor: pointer;
}
.chatbot a[href^="#source-card-"]:hover {
    color: var(--link-text-color-hover, #2563eb) !important;
    text-decoration: none;
}
html {
    scroll-behavior: smooth;
}
""") as demo:
    gr.Markdown("## Group 7 - Knowledge Base Retrieval Assistant")
    gr.Markdown("Using Azure AI Agents to answer any query and provide relevant files.")
    
    chatbot = gr.Chatbot(
        type="messages", 
        # label="Chat with Azure AI Agent",
        show_label=False,
        height="70vh",  # Use viewport height for responsive sizing
    )
    
    msg = gr.Textbox(
        placeholder="Type your query and press Enter...",
        show_label=False,
        container=False,
        max_lines=3
    )
        
    # Connect the input to the response function using chained events
    msg.submit(user, [msg, chatbot], [msg, chatbot], queue=False).then(
        bot, chatbot, chatbot
    )

if __name__ == "__main__":
    demo.launch(share=True)
