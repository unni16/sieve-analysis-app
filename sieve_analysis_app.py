import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import make_interp_spline
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

st.set_page_config(page_title="Sieve Analysis Tool", layout="centered")
st.title("🔬 Sieve Analysis Web App")
st.write("Enter weight retained on each sieve (comma-separated):")

# Fixed sieve sizes including pan (represented as 0.0 for now)
sieve_sizes = [4.75, 2.36, 1.18, 0.600, 0.300, 0.150, 0.075, 0.0]

# User input
user_input = st.text_input("Weight retained in grams (e.g. 150, 200, 250, ...)", "")

def create_pdf(df, D10, D30, D60, Cu, Cc, classification, plot_fig):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    styles = getSampleStyleSheet()
    elements.append(Paragraph("Sieve Analysis Report", styles['Heading1']))
    elements.append(Spacer(1, 12))

    # Table
    data = [["Sieve Size (mm)", "Weight Retained (g)", "% Retained", "Cum. % Retained", "% Passing"]]
    for idx, row in df.iterrows():
        sieve_label = "Pan" if row['Sieve Size (mm)'] == 0 else f"{row['Sieve Size (mm)']:.3f}"
        data.append([
            sieve_label,
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

    # Interpretation
    interpretation = f"""
    <b>D10</b>: {D10:.3f} mm<br/>
    <b>D30</b>: {D30:.3f} mm<br/>
    <b>D60</b>: {D60:.3f} mm<br/>
    <b>Cu</b>: {Cu:.2f}<br/>
    <b>Cc</b>: {Cc:.2f}<br/>
    <b>Classification</b>: {classification}
    """
    elements.append(Paragraph("Interpretation:", styles['Heading2']))
    elements.append(Paragraph(interpretation, styles['BodyText']))
    elements.append(Spacer(1, 12))

    # Plot
    img_buffer = BytesIO()
    plot_fig.savefig(img_buffer, format='png', bbox_inches='tight')
    img_buffer.seek(0)

    img = Image(img_buffer, width=400, height=250)
    elements.append(img)

    doc.build(elements)
    buffer.seek(0)
    return buffer

# Main app logic
if user_input:
    try:
        weight_retained = [float(x.strip()) for x in user_input.split(',')]
        if len(weight_retained) != len(sieve_sizes):
            st.error(f"Please enter exactly {len(sieve_sizes)} values.")
        else:
            df = pd.DataFrame({
                'Sieve Size (mm)': sieve_sizes,
                'Weight Retained (g)': weight_retained
            })

            total_weight = df['Weight Retained (g)'].sum()
            df['% Retained'] = (df['Weight Retained (g)'] / total_weight) * 100
            df['Cumulative % Retained'] = df['% Retained'].cumsum()
            df['% Passing'] = 100 - df['Cumulative % Retained']

            st.subheader("Sieve Analysis Table")
            st.dataframe(df)

            # Plot
            fig, ax = plt.subplots(figsize=(8, 5))
            plot_df = df[df['Sieve Size (mm)'] > 0]  # exclude pan

            x = plot_df['Sieve Size (mm)']
            y = plot_df['% Passing']

            x_smooth = np.logspace(np.log10(x.min()), np.log10(x.max()), 300)
            spline = make_interp_spline(np.log10(x), y, k=3)
            y_smooth = spline(np.log10(x_smooth))

            ax.semilogx(x_smooth, y_smooth, color='green')
            ax.scatter(x, y, color='black')  # actual data points

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

            classification = (
                "Fine soil (silt/clay)" if D10 < 0.075 else
                "Sand" if D10 < 2 else
                "Gravel or Coarse soil"
            )

            st.subheader("Interpretation")
            st.markdown(f"""
            - **D10** = {D10:.3f} mm  
            - **D30** = {D30:.3f} mm  
            - **D60** = {D60:.3f} mm  
            - **Coefficient of Uniformity (Cu)** = {Cu:.2f}  
            - **Coefficient of Curvature (Cc)** = {Cc:.2f}  
            - **Classification based on D10** = {classification}
            """)

            # Download PDF
            pdf_bytes = create_pdf(df, D10, D30, D60, Cu, Cc, classification, fig)
            st.download_button("📄 Download PDF Report", data=pdf_bytes, file_name="sieve_analysis_report.pdf", mime="application/pdf")

    except Exception as e:
        st.error(f"Error: {e}")
