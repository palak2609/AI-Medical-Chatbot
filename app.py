import gradio as gr
from src.multimodal import process

# -----------------------------
# Main Function
# -----------------------------
def app_function(audio, image, text):

    query, response, audio_output = process(
        audio_path=audio,
        text_input=text,
        image_path=image
    )

    return query, response, audio_output


# -----------------------------
# Custom CSS
# -----------------------------
custom_css = """
body {
    background-color: #f4f8fb;
}

.gradio-container {
    font-family: 'Segoe UI', sans-serif;
}

.main-title {
    text-align: center;
    font-size: 36px;
    font-weight: bold;
    color: #1565c0;
    margin-bottom: 5px;
}

.sub-title {
    text-align: center;
    font-size: 18px;
    color: #555;
    margin-bottom: 30px;
}

.section-title {
    font-size: 22px;
    font-weight: bold;
    color: #0d47a1;
    margin-bottom: 10px;
}

.footer {
    text-align: center;
    margin-top: 20px;
    color: gray;
    font-size: 14px;
}
"""


# -----------------------------
# UI
# -----------------------------
with gr.Blocks(css=custom_css) as demo:

    # Header
    gr.HTML("""
        <div class='main-title'>
            AI Medical Assistant
        </div>

        <div class='sub-title'>
            Voice + Vision + RAG + Emergency Detection
        </div>
    """)

    with gr.Row():

        # LEFT SIDE
        with gr.Column(scale=1):

            gr.HTML("<div class='section-title'>Patient Input</div>")

            audio_input = gr.Audio(
                sources=["microphone"],
                type="filepath",
                label="Voice Input"
            )

            image_input = gr.Image(
                type="filepath",
                label="Upload Medical Image"
            )

            text_input = gr.Textbox(
                placeholder="Describe your symptoms...",
                label="Text Symptoms"
            )

            submit_btn = gr.Button(
                "Analyze Symptoms",
                variant="primary"
            )

        # RIGHT SIDE
        with gr.Column(scale=1):

            gr.HTML("<div class='section-title'>AI Medical Analysis</div>")

            query_output = gr.Textbox(
                label="Transcribed / User Query",
                lines=2
            )

            response_output = gr.Textbox(
                label="AI Response",
                lines=18
            )

            audio_output = gr.Audio(
                label="Voice Response",
                autoplay=True
            )

    # Example Section
    gr.HTML("""
    <br>

    <div class='section-title'>
        Example Queries
    </div>

    <ul>
        <li>I have chest pain and breathing difficulty</li>
        <li>Analyze my acne image</li>
        <li>I have fever and headache</li>
        <li>How can I prevent skin infection?</li>
    </ul>
    """)

    # Footer
    gr.HTML("""
        <div class='footer'>
            AI-Powered Healthcare Assistant • Final Year Major Project
        </div>
    """)

    # Button Click
    submit_btn.click(
        fn=app_function,
        inputs=[
            audio_input,
            image_input,
            text_input
        ],
        outputs=[
            query_output,
            response_output,
            audio_output
        ]
    )

# Launch
demo.launch()