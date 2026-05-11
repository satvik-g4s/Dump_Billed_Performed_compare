import streamlit as st
import pandas as pd
import numpy as np
import time
from io import BytesIO

st.set_page_config(layout="wide")

st.title("6-Month Hours Reconciliation Checker")

# ---------------------------------------------------
# FILE UPLOAD SECTION
# ---------------------------------------------------

st.header("Upload Input Files")

uploaded_files = st.file_uploader(
    "Upload 6 CSV Files",
    type=["csv"],
    accept_multiple_files=True
)

st.caption("""Required Columns:Order Locn, Cust No, Order No, Billing Flag,Status, Rank/Design, Period To, Performed Hrs, Billed Hrs
Upload All 6 Dump Files Together in csv format UNTOUCHED, Header starts from row 3
""")

run_button = st.button("Run")

# ---------------------------------------------------
# PROCESSING SECTION
# ---------------------------------------------------

log_container = st.container()

if run_button:

    with log_container:

        status_text = st.empty()

        # ---------------------------------------------------
        # FILE VALIDATION
        # ---------------------------------------------------

        if not uploaded_files:
            st.error("Please upload 6 CSV files.")
            st.stop()

        if len(uploaded_files) != 6:
            st.error("Exactly 6 CSV files are required.")
            st.stop()

        status_text.info("Reading uploaded files...")
        time.sleep(0.5)

        required_columns = [
            "Order Locn",
            "Cust No",
            "Order No",
            "Billing Flag",
            "Rank/Design",
            "Period To",
            "Performed Hrs",
            "Billed Hrs",
            "Status"
        ]

        dfs = []
        check3_dfs = []

        for idx, uploaded_file in enumerate(uploaded_files, start=1):

            try:
                df = pd.read_csv(
                    uploaded_file,
                    header=2,
                    index_col=False,
                    usecols=required_columns,
                    encoding="latin1",
                    parse_dates=["Period To"],
                    dtype={
                        "Order Locn": "category",
                        "Cust No": "category",
                        "Billing Flag": "category",
                        "Rank/Design": "category",
                        "Performed Hrs": "float32",
                        "Billed Hrs": "float32",
                        "Status": "category",
                        "Order No": "category"
                    }
                )
                df = df[df["Status"].isin(["A", "O"])]
            except Exception as e:
                st.error(f"Error reading file {uploaded_file.name}: {e}")
                st.stop()

            missing_cols = [col for col in required_columns if col not in df.columns]

            if missing_cols:
                st.error(f"Missing columns in file {uploaded_file.name}: {missing_cols}")
                st.stop()

            dfs.append(df)

        status_text.success("Files loaded successfully.")
        time.sleep(0.5)
        # ---------------------------------------------------
        # PROCESSING LOGIC
        # ---------------------------------------------------

        billed_dict = {}
        perf_dict = {}

        status_text.info("Processing monthly datasets...")
        time.sleep(0.5)

        for i, df in enumerate(dfs):

            check3_temp = df.copy()
            try:
                month = df["Period To"].iloc[0].month
                year = df["Period To"].iloc[0].year
            except Exception as e:
                st.error(f"Error extracting month/year: {e}")
                st.stop()



            try:
                df = (
                        df.groupby(
                            ["Order Locn", "Cust No","Order No", "Billing Flag", "Rank/Design"],
                            as_index=False,
                            observed=True
                        )[["Performed Hrs", "Billed Hrs"]]
                        .sum()
                    )
            except Exception as e:
                st.error(f"Error during grouping step: {e}")
                st.stop()
            try:
                check3_temp = (
                    check3_temp.groupby(
                        ["Order Locn", "Cust No","Order No", "Billing Flag"],
                        as_index=False,
                        observed=True
                    )[["Performed Hrs", "Billed Hrs"]]
                    .sum()
                )
            
            except Exception as e:
                st.error(f"Error during Check3 grouping step: {e}")
                st.stop()

            try:
                month_key = int(f"{str(year)[-2:]}{month:02d}")

                month_label = f"{month:02d}-{str(year)[-2:]}"

                perf_col = f"Performed Hrs_{month_label}"
                bill_col = f"Billed Hrs_{month_label}"
                
                df.rename(
                    columns={
                        "Performed Hrs": perf_col,
                        "Billed Hrs": bill_col
                    },
                    inplace=True
                )
                check3_temp.rename(
                    columns={
                        "Performed Hrs": perf_col,
                        "Billed Hrs": bill_col
                    },
                    inplace=True
                )
                
                perf_dict[month_key] = perf_col
                billed_dict[month_key] = bill_col

            except Exception as e:
                st.error(f"Error renaming columns: {e}")
                st.stop()
            # IMPORTANT
            dfs[i] = df
            check3_dfs.append(check3_temp)

        status_text.success("Monthly processing completed.")
        time.sleep(0.5)

        # ---------------------------------------------------
        # MERGING
        # ---------------------------------------------------

        status_text.info("Optimizing and merging datasets...")
        time.sleep(0.5)
        
        try:
        
            optimized_dfs = []
        
            for df in dfs:
        
                # reduce memory usage
                for col in ["Order Locn", "Cust No","Order No", "Billing Flag", "Rank/Design"]:
                    df[col] = df[col].astype("category")
        
                df = df.set_index(
                    ["Order Locn", "Cust No","Order No", "Billing Flag", "Rank/Design"]
                )
        
                optimized_dfs.append(df)
        
            main_df = optimized_dfs[0]
        
            for df in optimized_dfs[1:]:
        
                main_df = main_df.join(
                    df,
                    how="outer"
                )
        
            main_df = main_df.reset_index()
            # ---------------------------------------------------
            # CHECK3 MERGE
            # ---------------------------------------------------
            
            try:
            
                optimized_check3_dfs = []
            
                for df in check3_dfs:
            
                    for col in ["Order Locn", "Cust No","Order No", "Billing Flag"]:
                        df[col] = df[col].astype("category")
            
                    df = df.set_index(
                        ["Order Locn", "Cust No","Order No", "Billing Flag"]
                    )
            
                    optimized_check3_dfs.append(df)
            
                check3_df = optimized_check3_dfs[0]
            
                for df in optimized_check3_dfs[1:]:
            
                    check3_df = check3_df.join(
                        df,
                        how="outer"
                    )
            
                check3_df = check3_df.reset_index()
            
            except Exception as e:
                st.error(f"Error during Check3 merge operation: {e}")
                st.stop()
        
        except Exception as e:
            st.error(f"Error during merge operation: {e}")
            st.stop()
        # ---------------------------------------------------
        # SORTING
        # ---------------------------------------------------

        status_text.info("Sorting final dataset...")
        time.sleep(0.5)

        try:
            main_df = main_df.sort_values(
                by=[
                    "Order Locn",
                    "Cust No",
                    "Order No",
                    "Billing Flag",
                    "Rank/Design"
                ]
            )
            check3_df = check3_df.sort_values(
                by=[
                    "Order Locn",
                    "Cust No",
                    "Order No",
                    "Billing Flag"
                ]
            )
            main_df = main_df.reset_index(drop=True)
            check3_df = check3_df.reset_index(drop=True)
        except Exception as e:
            st.error(f"Error during sorting: {e}")
            st.stop()

        # ---------------------------------------------------
        # COLUMN DETECTION
        # ---------------------------------------------------

        try:
            sorted_keys = sorted(perf_dict.keys())
        
            perf_cols = [perf_dict[k] for k in sorted_keys]
            billed_cols = [billed_dict[k] for k in sorted_keys]
        
        except Exception as e:
            st.error(f"Error detecting dynamic columns: {e}")
            st.stop()
        # ---------------------------------------------------
        # CHECK 1
        # ---------------------------------------------------

        status_text.info("Running Check 1...")
        time.sleep(0.5)



        try:
            comparison = np.isclose(
                main_df[perf_cols].values,
                main_df[billed_cols].values,
                equal_nan=True
            )

            main_df["6mon_1st"] = comparison.all(axis=1)

        except Exception as e:
            st.error(f"Error during check1_6mon: {e}")
            st.stop()

        try:
            comparison_3 = np.isclose(
            main_df[perf_cols[-3:]].values,
            main_df[billed_cols[-3:]].values,
            equal_nan=True
        )

            main_df["3mon_1st"] = comparison_3.all(axis=1)

        except Exception as e:
            st.error(f"Error during check1_3mon: {e}")
            st.stop()

        # ---------------------------------------------------
        # CHECK 2
        # ---------------------------------------------------

        status_text.info("Running Check 2...")
        time.sleep(0.5)

        try:
            all_6_cols = perf_cols + billed_cols

            main_df["6mon_2nd"] = (
                main_df[all_6_cols]
                .nunique(axis=1, dropna=False)
                .eq(1)
            )

        except Exception as e:
            st.error(f"Error during check_2_6mon: {e}")
            st.stop()

        try:
            all_3_cols = perf_cols[-3:] + billed_cols[-3:]

            main_df["3mon_2nd"] = (
                main_df[all_3_cols]
                .nunique(axis=1, dropna=False)
                .eq(1)
            )

        except Exception as e:
            st.error(f"Error during check_2_3mon: {e}")
            st.stop()

        # ---------------------------------------------------
        # CHECK 3
        # ---------------------------------------------------
        
        status_text.info("Running Check 3...")
        time.sleep(0.5)
        
        
        # ---------------------------------------------------
        # CHECK3 6 MONTH
        # ---------------------------------------------------
        
        try:
        
            comparison_6 = np.isclose(
                check3_df[perf_cols].values,
                check3_df[billed_cols].values,
                equal_nan=True
            )
        
            check3_df["6mon_3rd"] = comparison_6.all(axis=1)
        
        except Exception as e:
            st.error(f"Error during check3_6mon: {e}")
            st.stop()
        
        # ---------------------------------------------------
        # CHECK3 3 MONTH
        # ---------------------------------------------------
        
        try:
        
            comparison_3 = np.isclose(
                check3_df[perf_cols[-3:]].values,
                check3_df[billed_cols[-3:]].values,
                equal_nan=True
            )
        
            check3_df["3mon_3rd"] = comparison_3.all(axis=1)

            # ---------------------------------------------------
            # MERGE CHECK3 FLAGS BACK TO MAIN_DF
            # ---------------------------------------------------
            
            main_df = main_df.merge(
                check3_df[
                    [
                        "Order Locn",
                        "Cust No",
                        "Order No",
                        "Billing Flag",
                        "6mon_3rd",
                        "3mon_3rd"
                    ]
                ],
                on=[
                    "Order Locn",
                    "Cust No",
                    "Order No",
                    "Billing Flag"
                ],
                how="left"
            )
        
        except Exception as e:
            st.error(f"Error during check3_3mon: {e}")
            st.stop()

        

        # ---------------------------------------------------
        # OUTPUT GENERATION
        # ---------------------------------------------------

        status_text.info("Generating output file...")
        time.sleep(0.5)

        try:
            output = BytesIO()

            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                main_df.to_excel(
                    writer,
                    index=False,
                    sheet_name="Output"
                )
            
                check3_df.to_excel(
                    writer,
                    index=False,
                    sheet_name="Check3_Output"
                )

            output.seek(0)

        except Exception as e:
            st.error(f"Error generating output file: {e}")
            st.stop()

        status_text.success("Processing completed successfully.")

        st.download_button(
            label="Download Report",
            data=output,
            file_name="Billed-Performed-hours_Checks_output.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# ---------------------------------------------------
# DOCUMENTATION SECTION
# ---------------------------------------------------

with st.expander("What This Tool Does"):

    st.write("""
    This tool compares performed hours and billed hours across 6 monthly datasets.

    It performs multiple reconciliation checks:
    - Month-wise equality validation
    - Consistency validation across all months
    - Group-level reconciliation checks

    The final output highlights whether customer-level and group-level hours remain aligned over time.
    """)

with st.expander("How to Use"):

    st.write("""
    1. Upload all 6 monthly CSV files
    2. Click Run
    3. Wait for processing to complete
    4. Download the generated reconciliation report
    """)

with st.expander("Output Details"):

    st.write("""
    The output contains:
    
    - Original merged monthly data
    - Monthly performed hours
    - Monthly billed hours
    - 6-month reconciliation checks
    - Last 3-month reconciliation checks
    - Group-level validation results

    Grouping hierarchy:
    
    Order Location → Customer Number → Billing Flag → Rank/Design
    """)

with st.expander("Financial Logic"):

    st.write("""
    Check 1:
    Verifies whether performed hours exactly match billed hours month-wise.

    Check 2:
    Validates whether all monthly values remain consistent across the selected time period.

    Check 3:
    Performs customer-group level validation to ensure all related Rank/Design entries satisfy reconciliation conditions together.

    6-month checks use the complete uploaded timeline.

    3-month checks use only the latest 3 uploaded months.
    """)
