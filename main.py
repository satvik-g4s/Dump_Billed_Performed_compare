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

st.caption("""
Required Columns:
Order Locn, Cust No, Order No, Billing Flag, Status,
Rank/Design, Period To, Performed Hrs, Billed Hrs,
Adj Amount, Adj Remarks, Amount

Upload all 6 monthly CSV dump files together in untouched format.
Header starts from row 3.
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

        status_text.info(
            "Step 1/10: Reading and validating uploaded monthly dump files..."
        )
        time.sleep(0.1)

        required_columns = [
            "Order Locn",
            "Cust No",
            "Order No",
            "Billing Flag",
            "Rank/Design",
            "Period To",
            "Performed Hrs",
            "Billed Hrs",
            "Status",
            "Adj Amount",
            "Adj Remarks",
            "Amount"
        ]

        dfs = []
        check3_dfs = []

        for idx, uploaded_file in enumerate(uploaded_files, start=1):

            status_text.info(
                f"Reading file {idx}/6: {uploaded_file.name}"
            )
            time.sleep(0.1)

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
                        "Amount": "float32",
                        "Billed Hrs": "float32",
                        "Status": "category",
                        "Order No": "category",
                        "Adj Amount": "float32",
                        "Adj Remarks": "string"
                    }
                )

            except Exception as e:
                st.error(f"Error reading file {uploaded_file.name}: {e}")
                st.stop()

            missing_cols = [
                col for col in required_columns
                if col not in df.columns
            ]

            if missing_cols:
                st.error(
                    f"Missing columns in file {uploaded_file.name}: {missing_cols}"
                )
                st.stop()

            try:

                status_text.info(
                    f"Applying Status filter (A/O) on {uploaded_file.name}..."
                )
                time.sleep(0.1)

                df = df[df["Status"].isin(["A", "O"])]

            except Exception as e:
                st.error(f"Error filtering Status values: {e}")
                st.stop()

            try:

                status_text.info(
                    f"Transforming adjustment columns for {uploaded_file.name}..."
                )
                time.sleep(0.1)

                df["Adj Amount"] = (
                    df["Adj Amount"]
                    .fillna(0)
                    .ne(0)
                )

                df["Adj Remarks"] = (
                    df["Adj Remarks"]
                    .fillna("")
                    .astype(str)
                    .str.replace("-", "", regex=False)
                    .str.strip()
                    .ne("")
                )

            except Exception as e:
                st.error(
                    f"Error processing adjustment columns: {e}"
                )
                st.stop()

            dfs.append(df)

        status_text.success(
            "Step 1/10 Completed: All monthly files validated and loaded successfully."
        )
        time.sleep(0.1)

        # ---------------------------------------------------
        # PROCESSING LOGIC
        # ---------------------------------------------------

        billed_dict = {}
        perf_dict = {}
        adj_amt_dict = {}
        adj_rem_dict = {}
        amount_dict = {}

        status_text.info(
            "Step 2/10: Aggregating monthly reconciliation data..."
        )
        time.sleep(0.1)

        for i, df in enumerate(dfs):

            status_text.info(
                f"Processing monthly aggregation for dataset {i+1}/6..."
            )
            time.sleep(0.1)

            check3_temp = df.copy()

            try:

                month = df["Period To"].iloc[0].month
                year = df["Period To"].iloc[0].year

            except Exception as e:
                st.error(f"Error extracting month/year: {e}")
                st.stop()

            try:

                status_text.info(
                    "Creating rank-level grouped reconciliation structure..."
                )
                time.sleep(0.1)

                df = (
                    df.groupby(
                        [
                            "Order Locn",
                            "Cust No",
                            "Order No",
                            "Billing Flag",
                            "Rank/Design"
                        ],
                        as_index=False,
                        observed=True
                    ).agg({
                        "Performed Hrs": "sum",
                        "Billed Hrs": "sum",
                        "Amount": "sum",
                        "Adj Amount": "max",
                        "Adj Remarks": "max"
                    })
                )

            except Exception as e:
                st.error(f"Error during grouping step: {e}")
                st.stop()

            try:

                status_text.info(
                    "Creating billing-level grouped reconciliation structure..."
                )
                time.sleep(0.1)

                check3_temp = (
                    check3_temp.groupby(
                        [
                            "Order Locn",
                            "Cust No",
                            "Order No",
                            "Billing Flag"
                        ],
                        as_index=False,
                        observed=True
                    ).agg({
                        "Performed Hrs": "sum",
                        "Billed Hrs": "sum",
                        "Adj Amount": "max",
                        "Adj Remarks": "max"
                    })
                )

            except Exception as e:
                st.error(
                    f"Error during Check3 grouping step: {e}"
                )
                st.stop()

            try:

                month_key = int(
                    f"{str(year)[-2:]}{month:02d}"
                )

                month_label = (
                    f"{month:02d}-{str(year)[-2:]}"
                )

                status_text.info(
                    f"Generating dynamic month labels for {month_label}..."
                )
                time.sleep(0.1)

                perf_col = f"Performed Hrs_{month_label}"
                bill_col = f"Billed Hrs_{month_label}"
                adj_amt_col = f"Adj Amount_{month_label}"
                adj_rem_col = f"Adj Remarks_{month_label}"
                amount_col = f"Amount_{month_label}"

                df.rename(
                    columns={
                        "Performed Hrs": perf_col,
                        "Billed Hrs": bill_col,
                        "Adj Amount": adj_amt_col,
                        "Adj Remarks": adj_rem_col,
                        "Amount": amount_col
                    },
                    inplace=True
                )

                check3_temp.rename(
                    columns={
                        "Performed Hrs": perf_col,
                        "Billed Hrs": bill_col,
                        "Adj Amount": adj_amt_col,
                        "Adj Remarks": adj_rem_col,
                        "Amount": amount_col
                    },
                    inplace=True
                )

                perf_dict[month_key] = perf_col
                billed_dict[month_key] = bill_col
                adj_amt_dict[month_key] = adj_amt_col
                adj_rem_dict[month_key] = adj_rem_col
                amount_dict[month_key] = amount_col
                

            except Exception as e:
                st.error(f"Error renaming columns: {e}")
                st.stop()

            dfs[i] = df
            check3_dfs.append(check3_temp)

        status_text.success(
            "Step 2/10 Completed: Monthly datasets processed successfully."
        )
        time.sleep(0.1)

        # ---------------------------------------------------
        # MERGING
        # ---------------------------------------------------

        status_text.info(
            "Step 3/10: Merging monthly datasets into unified reconciliation structure..."
        )
        time.sleep(0.1)

        try:

            status_text.info(
                "Merging rank-level monthly datasets..."
            )
            time.sleep(0.1)

            optimized_dfs = []

            for df in dfs:

                for col in [
                    "Order Locn",
                    "Cust No",
                    "Order No",
                    "Billing Flag",
                    "Rank/Design"
                ]:
                    df[col] = df[col].astype("category")

                df = df.set_index(
                    [
                        "Order Locn",
                        "Cust No",
                        "Order No",
                        "Billing Flag",
                        "Rank/Design"
                    ]
                )

                optimized_dfs.append(df)

            main_df = optimized_dfs[0]

            for df in optimized_dfs[1:]:

                main_df = main_df.join(
                    df,
                    how="outer"
                )

            main_df = main_df.reset_index()

        except Exception as e:
            st.error(f"Error during merge operation: {e}")
            st.stop()

        try:

            status_text.info(
                "Merging billing-level grouped datasets..."
            )
            time.sleep(0.1)

            optimized_check3_dfs = []

            for df in check3_dfs:

                for col in [
                    "Order Locn",
                    "Cust No",
                    "Order No",
                    "Billing Flag"
                ]:
                    df[col] = df[col].astype("category")

                df = df.set_index(
                    [
                        "Order Locn",
                        "Cust No",
                        "Order No",
                        "Billing Flag"
                    ]
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
            st.error(
                f"Error during Check3 merge operation: {e}"
            )
            st.stop()

        status_text.success(
            "Step 3/10 Completed: Dataset merging completed successfully."
        )
        time.sleep(0.1)

        # ---------------------------------------------------
        # SORTING
        # ---------------------------------------------------

        status_text.info(
            "Step 4/10: Sorting reconciliation outputs chronologically and hierarchically..."
        )
        time.sleep(0.1)

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

        status_text.success(
            "Step 4/10 Completed: Output sorting completed successfully."
        )
        time.sleep(0.1)

        # ---------------------------------------------------
        # COLUMN DETECTION
        # ---------------------------------------------------

        status_text.info(
            "Step 5/10: Detecting and organizing dynamic monthly columns..."
        )
        time.sleep(0.1)

        try:

            sorted_keys = sorted(perf_dict.keys())

            perf_cols = [
                perf_dict[k]
                for k in sorted_keys
            ]

            billed_cols = [
                billed_dict[k]
                for k in sorted_keys
            ]

            adj_amt_cols = [
                adj_amt_dict[k]
                for k in sorted_keys
            ]

            adj_rem_cols = [
                adj_rem_dict[k]
                for k in sorted_keys
            ]

            amount_cols=[
                amount_dict[k]
                for k in sorted_keys
            ]
                

        except Exception as e:
            st.error(
                f"Error detecting dynamic columns: {e}"
            )
            st.stop()

        try:

            status_text.info(
                "Reordering monthly columns chronologically..."
            )
            time.sleep(0.1)

            identifier_cols = [
                "Order Locn",
                "Cust No",
                "Order No",
                "Billing Flag",
                "Rank/Design"
            ]

            ordered_month_cols = []

            for key in sorted_keys:

                ordered_month_cols.append(
                    perf_dict[key]
                )

                ordered_month_cols.append(
                    billed_dict[key]
                )

                ordered_month_cols.append(
                    adj_amt_dict[key]
                )

                ordered_month_cols.append(
                    adj_rem_dict[key]
                )

                ordered_month_cols.append(
                    amount_dict[key]
                )

            other_cols = [
                c for c in main_df.columns
                if c not in identifier_cols
                and c not in ordered_month_cols
            ]

            new_column_order = (
                identifier_cols +
                ordered_month_cols +
                other_cols
            )

            main_df = main_df[new_column_order]

        except Exception as e:
            st.error(
                f"Error while reordering columns: {e}"
            )
            st.stop()

        status_text.success(
            "Step 5/10 Completed: Monthly column organization completed."
        )
        time.sleep(0.1)

        # ---------------------------------------------------
        # CHECK 1
        # ---------------------------------------------------

        status_text.info(
            "Step 6/10: Running Check 1 - Month-wise Performed vs Billed validation..."
        )
        time.sleep(0.1)

        try:

            status_text.info(
                "Running 6-month exact reconciliation validation..."
            )
            time.sleep(0.1)

            comparison = np.isclose(
                main_df[perf_cols].values,
                main_df[billed_cols].values,
                equal_nan=True
            )

            main_df["6mon_1st"] = (
                comparison.all(axis=1)
            )

        except Exception as e:
            st.error(
                f"Error during check1_6mon: {e}"
            )
            st.stop()

        try:

            status_text.info(
                "Running latest 3-month exact reconciliation validation..."
            )
            time.sleep(0.1)

            comparison_3 = np.isclose(
                main_df[perf_cols[-3:]].values,
                main_df[billed_cols[-3:]].values,
                equal_nan=True
            )

            main_df["3mon_1st"] = (
                comparison_3.all(axis=1)
            )

        except Exception as e:
            st.error(
                f"Error during check1_3mon: {e}"
            )
            st.stop()

        status_text.success(
            "Step 6/10 Completed: Check 1 validation completed successfully."
        )
        time.sleep(0.1)

        # ---------------------------------------------------
        # CHECK 2
        # ---------------------------------------------------

        status_text.info(
            "Step 7/10: Running Check 2 - Cross-month consistency validation..."
        )
        time.sleep(0.1)

        try:

            status_text.info(
                "Checking consistency across all 6 months..."
            )
            time.sleep(0.1)

            all_6_cols = (
                perf_cols +
                billed_cols
            )

            main_df["6mon_2nd"] = (
                main_df[all_6_cols]
                .nunique(
                    axis=1,
                    dropna=False
                )
                .eq(1)
            )

        except Exception as e:
            st.error(
                f"Error during check_2_6mon: {e}"
            )
            st.stop()

        try:

            status_text.info(
                "Checking consistency across latest 3 months..."
            )
            time.sleep(0.1)

            all_3_cols = (
                perf_cols[-3:] +
                billed_cols[-3:]
            )

            main_df["3mon_2nd"] = (
                main_df[all_3_cols]
                .nunique(
                    axis=1,
                    dropna=False
                )
                .eq(1)
            )

        except Exception as e:
            st.error(
                f"Error during check_2_3mon: {e}"
            )
            st.stop()

        status_text.success(
            "Step 7/10 Completed: Check 2 consistency validation completed."
        )
        time.sleep(0.1)

        # ---------------------------------------------------
        # CHECK 3
        # ---------------------------------------------------

        status_text.info(
            "Step 8/10: Running Check 3 - Billing-level grouped reconciliation..."
        )
        time.sleep(0.1)

        try:

            status_text.info(
                "Running grouped 6-month billing reconciliation..."
            )
            time.sleep(0.1)

            comparison_6 = np.isclose(
                check3_df[perf_cols].values,
                check3_df[billed_cols].values,
                equal_nan=True
            )

            check3_df["6mon_3rd"] = (
                comparison_6.all(axis=1)
            )

        except Exception as e:
            st.error(
                f"Error during check3_6mon: {e}"
            )
            st.stop()

        try:

            status_text.info(
                "Running grouped latest 3-month billing reconciliation..."
            )
            time.sleep(0.1)

            comparison_3 = np.isclose(
                check3_df[perf_cols[-3:]].values,
                check3_df[billed_cols[-3:]].values,
                equal_nan=True
            )

            check3_df["3mon_3rd"] = (
                comparison_3.all(axis=1)
            )

            status_text.info(
                "Propagating grouped reconciliation results back to detailed output..."
            )
            time.sleep(0.1)

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
            st.error(
                f"Error during check3_3mon: {e}"
            )
            st.stop()

        status_text.success(
            "Step 8/10 Completed: Group-level reconciliation completed."
        )
        time.sleep(0.1)

        # ---------------------------------------------------
        # ADJUSTMENT FLAGS
        # ---------------------------------------------------

        status_text.info(
            "Step 9/10: Evaluating adjustment amount and remarks flags..."
        )
        time.sleep(0.1)

        try:

            status_text.info(
                "Generating 6-month adjustment indicators..."
            )
            time.sleep(0.1)

            main_df["Adj Amount_6mon"] = (
                main_df[adj_amt_cols]
                .any(axis=1)
            )

            main_df["Adj Remarks_6mon"] = (
                main_df[adj_rem_cols]
                .any(axis=1)
            )

            status_text.info(
                "Generating latest 3-month adjustment indicators..."
            )
            time.sleep(0.1)

            main_df["Adj Amount_3mon"] = (
                main_df[adj_amt_cols[-3:]]
                .any(axis=1)
            )

            main_df["Adj Remarks_3mon"] = (
                main_df[adj_rem_cols[-3:]]
                .any(axis=1)
            )

        except Exception as e:
            st.error(
                f"Error during adjustment flag checks: {e}"
            )
            st.stop()

        status_text.success(
            "Step 9/10 Completed: Adjustment flag generation completed."
        )
        time.sleep(0.1)

        # ---------------------------------------------------
        # CONSO FLAGS
        # ---------------------------------------------------

        try:

            status_text.info(
                "Generating consolidated billing-level reconciliation flags..."
            )
            time.sleep(0.1)

            conso_df = (
                main_df.groupby(
                    [
                        "Order Locn",
                        "Cust No",
                        "Order No",
                        "Billing Flag"
                    ],
                    as_index=False,
                    observed=True
                ).agg({
                    "6mon_1st": "min",
                    "3mon_1st": "min"
                })
            )

            main_df = main_df.merge(
                conso_df,
                on=[
                    "Order Locn",
                    "Cust No",
                    "Order No",
                    "Billing Flag"
                ],
                how="left",
                suffixes=("", "_conso")
            )

        except Exception as e:
            st.error(
                f"Error during consolidated reconciliation checks: {e}"
            )
            st.stop()

        status_text.success(
            "Consolidated reconciliation flags generated successfully."
        )
        time.sleep(0.1)

        # ---------------------------------------------------
        # AMOUNT CONSISTENCY CHECKS
        # ---------------------------------------------------
        
        try:
        
            status_text.info(
                "Running Amount consistency validation across 6 months..."
            )
            time.sleep(0.1)
        
            main_df["Amount_6mon_same"] = (
                main_df[amount_cols]
                .nunique(
                    axis=1,
                    dropna=False
                )
                .eq(1)
            )
        
            status_text.info(
                "Running Amount consistency validation across latest 3 months..."
            )
            time.sleep(0.1)
        
            main_df["Amount_3mon_same"] = (
                main_df[amount_cols[-3:]]
                .nunique(
                    axis=1,
                    dropna=False
                )
                .eq(1)
            )
        
        except Exception as e:
            st.error(
                f"Error during amount consistency checks: {e}"
            )
            st.stop()

        

        # ---------------------------------------------------
        # FINAL OUTPUT PREP
        # ---------------------------------------------------

        try:

            Final_df = main_df.copy()

            columns_to_keep = [
                "Order Locn",
                "Cust No",
                "Order No",
                "Billing Flag",
                "Rank/Design",
                "6mon_1st",
                "3mon_1st",
                "6mon_2nd",
                "3mon_2nd",
                "6mon_3rd",
                "3mon_3rd",
                "6mon_1st_conso",
                "3mon_1st_conso",
                "Amount_6mon_same",
                "Amount_3mon_same",
                "Adj Amount_6mon",
                "Adj Amount_3mon",
                "Adj Remarks_6mon",
                "Adj Remarks_3mon"                
            ]

            Final_df = Final_df[
                columns_to_keep
            ]

        except Exception as e:
            st.error(
                f"Error preparing final output sheet: {e}"
            )
            st.stop()

        # ---------------------------------------------------
        # OUTPUT GENERATION
        # ---------------------------------------------------

        status_text.info(
            "Step 10/10: Generating final reconciliation workbook..."
        )
        time.sleep(0.1)

        try:

            status_text.info(
                "Preparing output sheets and exporting workbook..."
            )
            time.sleep(0.1)

            output = BytesIO()

            with pd.ExcelWriter(
                output,
                engine="openpyxl"
            ) as writer:

                Final_df.to_excel(
                    writer,
                    index=False,
                    sheet_name="Check_Flags_Only"
                )

                main_df.to_excel(
                    writer,
                    index=False,
                    sheet_name="Detailed_Monthly_Data"
                )

                check3_df.to_excel(
                    writer,
                    index=False,
                    sheet_name="Check3_Output"
                )

            output.seek(0)

        except Exception as e:
            st.error(
                f"Error generating output file: {e}"
            )
            st.stop()

        status_text.success(
            "Reconciliation completed successfully. Final workbook is ready for download."
        )

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

with st.expander("Financial Logic & Reconciliation Checks"):

    st.write("""
    ### Overview
    This tool performs three distinct reconciliation checks to validate the alignment between performed hours and billed hours across a 6-month period.
    
    ---
    
    ### Check 1: Month-wise Equality Validation
    **What it does:**  
    Compares performed hours against billed hours for each individual month.
    
    **Logic:**  
    For each month, checks if `Performed Hrs == Billed Hrs` (allowing for floating-point precision).
    
    **Flags created:**
    - `6mon_1st`: TRUE if performed hours match billed hours for ALL 6 months
    - `3mon_1st`: TRUE if performed hours match billed hours for the LAST 3 months only
    
    ---
    
    ### Check 2: Cross-month Consistency Validation
    **What it does:**  
    Verifies that all monthly values (both performed and billed hours) remain consistent across the time period.
    
    **Logic:**  
    Checks if every value in the combined set of performed and billed hours (12 values total for 6 months) is identical.
    
    **Flags created:**
    - `6mon_2nd`: TRUE if all 12 monthly values are the same across all 6 months
    - `3mon_2nd`: TRUE if all values are consistent across the last 3 months
    
    ---
    
    ### Check 3: Group-level Reconciliation
    **What it does:**  
    Performs validation at the customer-group level, ignoring individual Rank/Design breakdowns.
    
    **Logic:**  
    Groups data by Order Location, Customer Number, Order Number, and Billing Flag (aggregating all Rank/Design entries). Then applies the same equality check as Check 1.
    
    **Flags created:**
    - `6mon_3rd`: TRUE if grouped performed hours match grouped billed hours for all 6 months
    - `3mon_3rd`: TRUE if grouped values match for the last 3 months
    
    ---
    
    ### Consolidated Flags
    **What they do:**  
    `6mon_1st_conso` and `3mon_1st_conso` show whether ALL Rank/Design entries within the same customer group passed Check 1.
    
    **Logic:**  
    For each unique combination of (Order Locn, Cust No, Order No, Billing Flag), checks if every associated Rank/Design entry has TRUE in Check 1.
    
    **Result:**
    - TRUE if ALL Rank/Design entries in the group passed Check 1
    - FALSE if ANY Rank/Design entry in the group failed Check 1
    
    ---
    
    ### Adjustment Flags
    **Adj Amount_6mon / Adj Amount_3mon:**  
    TRUE if there was any adjustment amount recorded in the respective time period.
    
    **Adj Remarks_6mon / Adj Remarks_3mon:**  
    TRUE if there were any adjustment remarks (non-empty, non-dash) in the respective time period.
    
    ---
    
    ### Time Period Definitions
    - **6-month checks:** Use all 6 uploaded months in chronological order (Month 1 through Month 6)
    - **3-month checks:** Use only the last 3 uploaded months (Month 4, 5, and 6)

    ### Data Quality Notes
    - Only records with Status 'A' (Active) or 'O' (Open) are included;
    - Empty adjustment remarks or dashes '-' are treated as no remark
    """)
    
