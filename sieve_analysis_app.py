import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from scipy.interpolate import interp1d

st.set_page_config(page_title="Sieve Analysis Tool", layout="centered")
st.title("🔬 Sieve Analysis Web App")
st.write("Enter weight retained on each sieve (comma-separated):")

# Fixed sieve sizes
sieve_sizes = [4.75, 2.36, 1.88, 0.600, 0.300, 0.150, 0.075, 0.0]  # Added 0.0 for pan

# User input
user_input = st.text_input("Weight retained in grams (e.g. 150, 200, 250, ...)", "")

def create_pdf(df, D10, D30, D60, Cu, Cc, plot_fig):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    styles = getSampleStyleSheet()
    elements.append(Paragraph("Sieve Analysis Report", styles['Heading1']))
    elements.append(Spacer(1, 12))

    # Table
    data = [["Sieve Size (mm)", "Weight Retained (g)", "% Retained", "Cum. % Retained", "% Passing"]]
    for _, row in df.iterrows():
        data.append([
            f"{row['Sieve Size (mm)']:.3f}" if row['Sieve Size (mm)'] != 0 else "Pan",
            f"{row['Weight Retained (g)']:.2f}",
            f"{row['% Retained']:.2f}",
            f"{row['Cumulative % Retained']:.2f}",
            f"{row['% Passing']:.2f}"
        ])

    table = Table(data, hAlign='LEFT')
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, -1), 9)
    ]))
    elements.append(table)
    elements.append(Spacer(1, 12))

    # Plot
    img_buffer = BytesIO()
    plot_fig.savefig(img_buffer, format='png', bbox_inches='tight')
    img_buffer.seek(0)

    # Correct way to add image
    img = Image(img_buffer, width=400, height=250)
    elements.append(img)

    doc.build(elements)
    buffer.seek(0)
    return buffer

# Main app logic
if user_input:
    try:
        weight_retained = [float(x.strip()) for x in user_input.split(',')]
        if len(weight_retained) != len(sieve_sizes) - 1:  # Exclude pan from input
            st.error(f"Please enter exactly {len(sieve_sizes) - 1} values.")
        else:
            df = pd.DataFrame({
                'Sieve Size (mm)': sieve_sizes[:-1],  # Exclude pan
                'Weight Retained (g)': weight_retained
            })

            total_weight = df['Weight Retained (g)'].sum()
            df['% Retained'] = (df['Weight Retained (g)'] / total_weight) * 100
            df['Cumulative % Retained'] = df['% Retained'].cumsum()
            df['% Passing'] = 100 - df['Cumulative % Retained']

            st.subheader("Sieve Analysis Table")
            st.dataframe(df)

            # Smooth line plotting using interpolation
            x = df['Sieve Size (mm)']
            y = df['% Passing']

            # Ensure interpolation only occurs for valid data points
            f = interp1d(x, y, kind='cubic', fill_value="extrapolate")
            x_new = np.logspace(np.log10(0.01), np.log10(10), 500)  # Creating a log scale for x-axis
            y_new = f(x_new)

            # Plot
            fig, ax = plt.subplots(figsize=(8, 5))
            ax.plot(x_new, y_new, color='green')
            ax.set_xticks([0.01, 0.1, 1, 10])
            ax.get_xaxis().set_major_formatter(plt.ScalarFormatter())
            ax.ticklabel_format(axis='x', style='plain')

            ax.grid(True, which='both', linestyle='--', linewidth=0.5)
            ax.set_xlabel("Sieve Size (mm) [Log Scale]")
            ax.set_ylabel("Cumulative % Passing")
            ax.set_title("Particle Size Distribution Curve")
            st.pyplot(fig)

            # Interpretation
            def interpolate_diameter(percent):
                return np.interp(percent, df['% Passing'][::-1], df['Sieve Size (mm)'][::-1])

            D10 = interpolate_diameter(10)
            D30 = interpolate_diameter(30)
            D60 = interpolate_diameter(60)
            Cu = D60 / D10 if D10 else float('inf')
            Cc = (D30 ** 2) / (D10 * D60) if D10 and D60 else float('inf')

            st.subheader("Interpretation")
            st.markdown(f"""
            - **D10** = {D10:.3f} mm  
            - **D30** = {D30:.3f} mm  
            - **D60** = {D60:.3f} mm  
            - **Coefficient of Uniformity (Cu)** = {Cu:.2f}  
            - **Coefficient of Curvature (Cc)** = {Cc:.2f}  
            """)

            # Download PDF
            pdf_bytes = create_pdf(df, D10, D30, D60, Cu, Cc, fig)
            st.download_button("📄 Download PDF Report", data=pdf_bytes, file_name="sieve_analysis_report.pdf", mime="application/pdf")

    except Exception as e:
        st.error(f"Error: {e}")
