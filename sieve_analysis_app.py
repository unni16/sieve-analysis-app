import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

st.set_page_config(page_title="Sieve Analysis Tool", layout="centered")
st.title("🔬 Sieve Analysis Web App")
st.write("Enter weight retained on each sieve (comma-separated):")

# Sieve sizes including pan
sieve_sizes = [4.75, 2.36, 1.18, 0.600, 0.300, 0.150, 0.075, 0.0]

# User input
user_input = st.text_input("Weight retained in grams (e.g. 150, 200, 250, ...)", "")

def interpolate_diameter(df, percent):
    return np.interp(percent, df['% Passing'][::-1], df['Sieve Size (mm)'][::-1])

def create_pdf(df, plot_fig, interpretation_text):
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
            f"{row['Sieve Size (mm)']:.3f}",
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

    # Plot image
    img_buffer = BytesIO()
    plot_fig.savefig(img_buffer, format='png', bbox_inches='tight')
    img_buffer.seek(0)
    img = Image(img_buffer, width=400, height=250)
    elements.append(img)
    elements.append(Spacer(1, 12))

    # Interpretation text
    elements.append(Paragraph("Interpretation", styles['Heading2']))
    elements.append(Paragraph(interpretation_text, styles['Normal']))

    doc.build(elements)
    buffer.seek(0)
    return buffer

if user_input:
    try:
        weight_retained = [float(x.strip()) for x in user_input.split(',')]
        if len(weight_retained) != len(sieve_sizes):
            st.error(f"Please enter exactly {len(sieve_sizes)} values (including pan).")
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

            # Interpolation for interpretation
            interp_df = df[df['Sieve Size (mm)'] > 0.0]
            d10 = interpolate_diameter(interp_df, 10)
            d30 = interpolate_diameter(interp_df, 30)
            d60 = interpolate_diameter(interp_df, 60)
            cu = d60 / d10 if d10 != 0 else np.nan
            cc = (d30 ** 2) / (d10 * d60) if d10 != 0 and d60 != 0 else np.nan

            # Interpretation without gradation text
            interpretation_text = (
                f"D10 = {d10:.3f} mm<br/>"
                f"D30 = {d30:.3f} mm<br/>"
                f"D60 = {d60:.3f} mm<br/>"
                f"Uniformity Coefficient (Cu) = {cu:.2f}<br/>"
                f"Coefficient of Curvature (Cc) = {cc:.2f}"
            )

            st.subheader("Interpretation")
            st.markdown(interpretation_text, unsafe_allow_html=True)

            # Filter for plot (exclude pan)
            plot_df = interp_df

            fig, ax = plt.subplots(figsize=(8, 5))
            ax.semilogx(plot_df['Sieve Size (mm)'], plot_df['% Passing'], marker='o', color='green')
            ax.set_xticks([0.075, 0.15, 0.3, 0.6, 1.18, 2.36, 4.75])
            ax.get_xaxis().set_major_formatter(plt.ScalarFormatter())
            ax.ticklabel_format(axis='x', style='plain')
            ax.grid(True, which='both', linestyle='--', linewidth=0.5)
            ax.set_xlabel("Sieve Size (mm) [Log Scale]")
            ax.set_ylabel("Cumulative % Passing")
            ax.set_title("Particle Size Distribution Curve")
            st.pyplot(fig)

            # PDF
            pdf_bytes = create_pdf(df, fig, interpretation_text)
            st.download_button("📄 Download PDF Report", data=pdf_bytes, file_name="sieve_analysis_report.pdf", mime="application/pdf")

    except Exception as e:
        st.error(f"Error: {e}")
