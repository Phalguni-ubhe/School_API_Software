import os
import pandas as pd
import pdfplumber
import re

class ResultAnalyzer:
    def __init__(self):
        self.subject_codes = {
            '301': 'ENGLISH CORE',
            '302': 'HINDI CORE',
            '041': 'MATHEMATICS',
            '042': 'PHYSICS',
            '043': 'CHEMISTRY',
            '044': 'BIOLOGY',
            '048': 'PHYSICAL EDUCATION',
            '030': 'ECONOMICS',
            '054': 'BUSINESS STUDIES',
            '055': 'ACCOUNTANCY',
            '083': 'COMPUTER SCIENCE',
            '027': 'HISTORY',
            '028': 'POLITICAL SCIENCE',
            '029': 'GEOGRAPHY',
            '037': 'PSYCHOLOGY',
            '802': 'INFORMATION TECHNOLOGY',
            '803': 'AI',
            '804': 'PAT'
        }

        self.grade_ranges = [
            (95, 100, 10, '>95'),
            (90, 94.99, 8, '90-94.99'),
            (80, 89.99, 6, '80-89.9'),
            (70, 79.99, 4, '70-79.9'),
            (60, 69.99, 2, '60-69.9'),
            (50, 59.99, 0, '50-59.99'),
            (33, 49.99, -1, '33-49.99'),
            (1, 32.99, -2, 'Compartment'),
            (0, 0.99, -3, 'Fail')
        ]

    def process_pdf_result(self, pdf_path):
        try:
            print(f"Processing: {pdf_path}")
            with pdfplumber.open(pdf_path) as pdf:
                all_text = "\n".join(page.extract_text() for page in pdf.pages)

            students_data = self.extract_student_data(all_text)
            if not students_data:
                print(f"No student data found in {pdf_path}")
                return None

            return pd.DataFrame(students_data)

        except Exception as e:
            print(f"Error processing {pdf_path}: {str(e)}")
            return None

    def extract_student_data(self, text):
        students = []
        blocks = re.split(r'Roll No:\s*', text)[1:]

        for block in blocks:
            try:
                roll_match = re.search(r'(\d{7,})', block)
                name_match = re.search(r'Candidate Name:\s*(.+)', block)
                if not roll_match or not name_match:
                    continue

                roll_number = roll_match.group(1).strip()
                name = name_match.group(1).strip()

                student = {'Roll_Number': roll_number, 'Name': name}
                for code in self.subject_codes:
                    student[code] = None  # Assume subject not taken

                for code, subject in self.subject_codes.items():
                    patterns = [
                        rf'{subject.upper()}.*?(\d{{1,3}})',
                        rf'{code}\s+([A-Z\s]*)\s*(\d{{1,3}})',
                        rf'{subject.upper().replace(" ", "")}.*?(\d{{1,3}})'
                    ]
                    for pattern in patterns:
                        match = re.search(pattern, block, re.IGNORECASE | re.DOTALL)
                        if match:
                            marks = int(match.group(1)) if match.lastindex == 1 else int(match.group(2))
                            if 0 <= marks <= 100:
                                student[code] = marks
                                break

                students.append(student)

            except Exception as e:
                print(f"Error in block: {e}")
                continue

        return students

    def create_simplified_results(self, df):
        return df[['Roll_Number', 'Name'] + list(self.subject_codes.keys())].copy()

    def calculate_api_for_subject(self, marks_series):
        valid_marks = marks_series.dropna()
        total_students = len(valid_marks)
        if total_students == 0:
            return 0

        total_points = 0
        for min_m, max_m, pts, label in self.grade_ranges:
            if label == 'Fail':
                count = sum(valid_marks == 0)
            else:
                count = sum((valid_marks >= min_m) & (valid_marks <= max_m))
            total_points += count * pts
        return round(total_points / total_students, 2)

    def save_subject_api(self, subject_code, subject_name, marks_series, output_dir):
        subject_api_dir = os.path.join(output_dir, 'subject_api')
        os.makedirs(subject_api_dir, exist_ok=True)

        valid_marks = marks_series.dropna()
        grade_data = []
        for min_m, max_m, pts, label in self.grade_ranges:
            if label == 'Fail':
                count = sum(valid_marks == 0)
            else:
                count = sum((valid_marks >= min_m) & (valid_marks <= max_m))
            grade_data.append({'Grade_Range': label, 'Count': count, 'Points': pts})

        api = self.calculate_api_for_subject(marks_series)
        grade_data.append({'Grade_Range': 'TOTAL/API', 'Count': len(valid_marks), 'Points': api})

        df = pd.DataFrame(grade_data)
        df.to_csv(os.path.join(subject_api_dir, f"{subject_code}_{subject_name}_API.csv"), index=False)
        print(f"Saved {subject_name} API")

    def generate_api_table(self, df):
        api_data = []
        for code, name in self.subject_codes.items():
            marks = df[code]
            valid_marks = marks.dropna()
            total = len(valid_marks)
            appeared = sum(valid_marks > 0)
            passed = sum(valid_marks >= 33)

            counts = {}
            for min_m, max_m, pts, label in self.grade_ranges:
                if label == 'Fail':
                    count = sum(valid_marks == 0)
                elif label == 'Compartment':
                    count = sum((valid_marks >= 1) & (valid_marks <= 32))
                else:
                    count = sum((valid_marks >= min_m) & (valid_marks <= max_m))
                counts[label] = count

            api = self.calculate_api_for_subject(valid_marks)
            row = {
                'SNO': list(self.subject_codes.keys()).index(code) + 1,
                'Name of APS': name,
                'Total Students in School as on 31 Mar 2025': total,
                'No of students appeared': appeared,
                'No of students pass': passed,
                '>95': counts.get('>95', 0),
                '>90': counts.get('90-94.99', 0),
                '>80': counts.get('80-89.9', 0),
                '>70': counts.get('70-79.9', 0),
                '>60': counts.get('60-69.9', 0),
                '>50': counts.get('50-59.99', 0),
                '>33': counts.get('33-49.99', 0),
                'Compartment': counts.get('Compartment', 0),
                'Fail': counts.get('Fail', 0),
                'API': api
            }
            api_data.append(row)

        return pd.DataFrame(api_data)

    def generate_overall_api(self, df, output_dir):
        all_marks = []
        for code in self.subject_codes.keys():
            all_marks.extend(df[code].dropna().tolist())

        marks_series = pd.Series(all_marks)
        total_points = 0
        overall_rows = []

        for min_m, max_m, pts, label in self.grade_ranges:
            if label == 'Fail':
                count = sum(marks_series == 0)
            else:
                count = sum((marks_series >= min_m) & (marks_series <= max_m))
            points = count * pts
            total_points += points
            overall_rows.append({
                'Grade': label,
                'Points to be Awarded': pts,
                'No of Students': count,
                'Points': points
            })

        total_students = len(marks_series)
        overall_api = round(total_points / total_students, 2) if total_students else 0

        overall_rows.append({'Grade': 'TOTAL', 'Points to be Awarded': '', 'No of Students': '', 'Points': total_points})
        overall_rows.append({'Grade': 'OVERALL API', 'Points to be Awarded': '', 'No of Students': total_students, 'Points': overall_api})

        overall_df = pd.DataFrame(overall_rows)
        overall_path = os.path.join(output_dir, 'overall_api.csv')
        overall_df.to_csv(overall_path, index=False)
        print(f"\nSaved OVERALL API report to: {overall_path}")

    def process_all_results(self):
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
        data_dir = os.path.join(project_root, 'data', 'class_12')
        output_dir = os.path.join(project_root, 'output', 'class_12')
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

        pdf_files = [os.path.join(root, file)
                     for root, _, files in os.walk(data_dir)
                     for file in files if file.endswith('.pdf')]

        if not pdf_files:
            print(f"No PDF files found in {data_dir}")
            return

        all_results = []
        for pdf in pdf_files:
            result = self.process_pdf_result(pdf)
            if result is not None:
                all_results.append(result)

        if not all_results:
            print("No results could be processed")
            return

        combined_df = pd.concat(all_results, ignore_index=True)
        simplified_df = self.create_simplified_results(combined_df)

        simplified_path = os.path.join(output_dir, '12th_result.csv')
        simplified_df.to_csv(simplified_path, index=False)
        print(f"\nSaved simplified result to: {simplified_path}")

        for code, name in self.subject_codes.items():
            self.save_subject_api(code, name, simplified_df[code], output_dir)

        summary_df = self.generate_api_table(simplified_df)
        summary_path = os.path.join(output_dir, 'subject_api', 'Subject_Wise_API_Summary.csv')
        summary_df.to_csv(summary_path, index=False)
        print(f"\nSaved subject-wise API summary to: {summary_path}")

        self.generate_overall_api(simplified_df, output_dir)

        print(f"\nProcessed {len(simplified_df)} students.")
        print("\n" + "-" * 100)
        print(summary_df.to_string(index=False))
        print("-" * 100)

import sys
import json

def main():
    analyzer = ResultAnalyzer()
    # Accept up to 3 PDF paths as arguments
    pdf_files = sys.argv[1:]
    results = {}
    all_dfs = []
    stream_names = ['science', 'commerce', 'humanities']
    for idx, pdf_path in enumerate(pdf_files):
        if not os.path.exists(pdf_path):
            results[stream_names[idx]] = {'error': f'File not found: {pdf_path}'}
            continue
        df = analyzer.process_pdf_result(pdf_path)
        if df is None or df.empty:
            results[stream_names[idx]] = {'error': f'Could not process: {pdf_path}'}
            continue
        simplified_df = analyzer.create_simplified_results(df)
        # Subject-wise APIs
        subject_apis = {}
        for code, name in analyzer.subject_codes.items():
            api = analyzer.calculate_api_for_subject(simplified_df[code])
            subject_apis[name] = api
        # Overall API
        all_marks = []
        for code in analyzer.subject_codes.keys():
            all_marks.extend(simplified_df[code].dropna().tolist())
        marks_series = pd.Series(all_marks)
        overall_api = analyzer.calculate_api_for_subject(marks_series)
        results[stream_names[idx]] = {
            'subject_apis': subject_apis,
            'overall_api': overall_api,
            'students': simplified_df[['Roll_Number', 'Name']].to_dict(orient='records')
        }
        if not simplified_df.empty:
            all_dfs.append(simplified_df)

    # Combined summary for all streams
    if all_dfs:
        combined_df = pd.concat(all_dfs, ignore_index=True)
        combined_subject_apis = {}
        for code, name in analyzer.subject_codes.items():
            api = analyzer.calculate_api_for_subject(combined_df[code])
            combined_subject_apis[name] = api
        all_marks = []
        for code in analyzer.subject_codes.keys():
            all_marks.extend(combined_df[code].dropna().tolist())
        marks_series = pd.Series(all_marks)
        combined_overall_api = analyzer.calculate_api_for_subject(marks_series)
        results['combined'] = {
            'subject_apis': combined_subject_apis,
            'overall_api': combined_overall_api,
            'students': combined_df[['Roll_Number', 'Name']].to_dict(orient='records')
        }

        # Save output files for combined results
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
        output_dir = os.path.join(project_root, 'output', 'class_12')
        os.makedirs(output_dir, exist_ok=True)
        simplified_path = os.path.join(output_dir, '12th_result.csv')
        combined_df.to_csv(simplified_path, index=False)
        # Subject-wise APIs
        subject_api_dir = os.path.join(output_dir, 'subject_api')
        os.makedirs(subject_api_dir, exist_ok=True)
        for code, name in analyzer.subject_codes.items():
            marks_series_subj = combined_df[code]
            valid_marks = marks_series_subj.dropna()
            grade_data = []
            for min_m, max_m, pts, label in analyzer.grade_ranges:
                if label == 'Fail':
                    count = sum(valid_marks == 0)
                else:
                    count = sum((valid_marks >= min_m) & (valid_marks <= max_m))
                grade_data.append({'Grade_Range': label, 'Count': count, 'Points': pts})
            api = analyzer.calculate_api_for_subject(marks_series_subj)
            grade_data.append({'Grade_Range': 'TOTAL/API', 'Count': len(valid_marks), 'Points': api})
            df_api = pd.DataFrame(grade_data)
            df_api.to_csv(os.path.join(subject_api_dir, f"{code}_{name}_API.csv"), index=False)
        # Subject-wise summary
        summary_df = analyzer.generate_api_table(combined_df)
        summary_path = os.path.join(subject_api_dir, 'Subject_Wise_API_Summary.csv')
        summary_df.to_csv(summary_path, index=False)
        # Overall API
        overall_rows = []
        total_points = 0
        for min_m, max_m, pts, label in analyzer.grade_ranges:
            if label == 'Fail':
                count = sum(marks_series == 0)
            else:
                count = sum((marks_series >= min_m) & (marks_series <= max_m))
            points = count * pts
            total_points += points
            overall_rows.append({
                'Grade': label,
                'Points to be Awarded': pts,
                'No of Students': count,
                'Points': points
            })
        total_students = len(marks_series)
        overall_api = round(total_points / total_students, 2) if total_students else 0
        overall_rows.append({'Grade': 'TOTAL', 'Points to be Awarded': '', 'No of Students': '', 'Points': total_points})
        overall_rows.append({'Grade': 'OVERALL API', 'Points to be Awarded': '', 'No of Students': total_students, 'Points': overall_api})
        overall_df = pd.DataFrame(overall_rows)
        overall_path = os.path.join(output_dir, 'overall_api.csv')
        overall_df.to_csv(overall_path, index=False)

    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
