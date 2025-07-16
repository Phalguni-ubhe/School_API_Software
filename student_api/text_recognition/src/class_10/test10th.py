import os
import re
import pandas as pd
import pdfplumber

class ResultAnalyzer10th:
    def __init__(self):
        self.subject_codes = {
            '184': 'ENGLISH',
            '085': 'HINDI',
            '241': 'MATHEMATICS',
            '086': 'SCIENCE',
            '087': 'SOCIAL SCIENCE',
            '402': 'IT'
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

    def extract_text_from_pdf(self, pdf_path):
        try:
            with pdfplumber.open(pdf_path) as pdf:
                return "\n".join(page.extract_text() or "" for page in pdf.pages)
        except Exception as e:
            print(f"Failed to extract: {e}")
            return ""

    def extract_student_blocks(self, text):
        lines = text.splitlines()
        blocks = []
        current = []

        for line in lines:
            if re.search(r'Roll\s*No[:\s]\s*\d+', line, re.IGNORECASE):
                if current:
                    blocks.append("\n".join(current))
                    current = []
            current.append(line)
        if current:
            blocks.append("\n".join(current))
        return blocks

    def extract_student_info(self, block):
        info = {}
        match = re.search(r'Roll\s*No[:\s]+(\d+)', block)
        if match:
            info['Roll_Number'] = match.group(1)

        match = re.search(r'Name[:\s]+([A-Z\s]+)', block)
        if match:
            info['Name'] = match.group(1).strip()

        return info if 'Roll_Number' in info and 'Name' in info else None

    def extract_marks(self, block):
        marks = {}
        for code, name in self.subject_codes.items():
            pattern = rf'{code}\s+{name}.*?(\d{{1,3}})'
            match = re.search(pattern, block, re.IGNORECASE)
            if match:
                m = int(match.group(1))
                if 0 <= m <= 100:
                    marks[code] = m
        return marks

    def process_pdf(self, path):
        text = self.extract_text_from_pdf(path)
        blocks = self.extract_student_blocks(text)
        all_students = []

        for block in blocks:
            info = self.extract_student_info(block)
            if not info:
                continue
            marks = self.extract_marks(block)
            if not marks:
                continue
            student = {
                'Roll_Number': info['Roll_Number'],
                'Name': info['Name']
            }
            for code in self.subject_codes:
                student[code] = marks.get(code, None)
            all_students.append(student)
        return pd.DataFrame(all_students)

    def calculate_best_of_5(self, df):
        simplified = []
        for _, row in df.iterrows():
            data = {
                'Roll_Number': row['Roll_Number'],
                'Name': row['Name']
            }
            for code in self.subject_codes:
                data[code] = row[code] if not pd.isna(row[code]) else None
            scores = [row[code] for code in self.subject_codes if not pd.isna(row[code])]
            scores.sort(reverse=True)
            if len(scores) >= 5:
                data['Best_of_5'] = sum(scores[:5])
                data['Percentage'] = round(sum(scores[:5]) / 500 * 100, 2)
            else:
                data['Best_of_5'] = 0
                data['Percentage'] = 0
            simplified.append(data)
        return pd.DataFrame(simplified)

    def save_subject_api(self, df, subject_code, output_dir):
        series = df[subject_code].dropna()
        total = len(series)
        grade_data = []
        total_points = 0

        for min_m, max_m, pts, label in self.grade_ranges:
            count = sum((series >= min_m) & (series <= max_m)) if label != 'Fail' else sum(series == 0)
            points = count * pts
            grade_data.append({
                'Range': label,
                'Points to be Awarded': pts,
                'no of students': count,
                'POINTS': points
            })
            total_points += points

        grade_data.append({'Range': 'Total', 'Points to be Awarded': '', 'no of students': total, 'POINTS': total_points})
        api = round(total_points / total, 2) if total > 0 else '#DIV/0!'
        grade_data.append({'Range': 'API', 'Points to be Awarded': '', 'no of students': total, 'POINTS': api})

        subject_api_dir = os.path.join(output_dir, 'subject_api')
        os.makedirs(subject_api_dir, exist_ok=True)

        df_api = pd.DataFrame(grade_data)
        df_api.to_csv(os.path.join(subject_api_dir, f'API_{self.subject_codes[subject_code]}.csv'), index=False)

    def generate_api_summary(self, df):
        rows = []
        for i, (code, name) in enumerate(self.subject_codes.items(), start=1):
            series = df[code].dropna()
            total = len(series)
            row = {
                'SNO': i,
                'Name of APS': name,
                'Total Students': total,
                'Appeared': total,
                'Passed': sum(series >= 33),
                '>95': sum(series > 95),
                '>90': sum((series > 90) & (series <= 95)),
                '>80': sum((series > 80) & (series <= 90)),
                '>70': sum((series > 70) & (series <= 80)),
                '>60': sum((series > 60) & (series <= 70)),
                '>50': sum((series > 50) & (series <= 60)),
                '>33': sum((series > 33) & (series <= 50)),
                'Compartment': sum((series >= 1) & (series <= 32)),
                'Fail': sum(series == 0)
            }
            points = (
                row['>95'] * 10 + row['>90'] * 8 + row['>80'] * 6 + row['>70'] * 4 +
                row['>60'] * 2 + row['>50'] * 0 + row['>33'] * -1 +
                row['Compartment'] * -2 + row['Fail'] * -3
            )
            row['API'] = round(points / total, 2) if total > 0 else '#DIV/0!'
            rows.append(row)
        return pd.DataFrame(rows)

    def generate_overall_api_report(self, df, output_dir):
        all_marks = []
        for code in self.subject_codes:
            all_marks.extend(df[code].dropna().tolist())

        marks_series = pd.Series(all_marks)
        total_points = 0
        total_students = len(marks_series)

        overall_rows = []
        for min_m, max_m, pts, label in self.grade_ranges:
            if label == 'Fail':
                count = sum(marks_series == 0)
            else:
                count = sum((marks_series >= min_m) & (marks_series <= max_m))
            points = count * pts
            total_points += points
            overall_rows.append({
                'Range': label,
                'Points to be Awarded': pts,
                'no of students': count,
                'POINTS': points
            })

        overall_rows.append({'Range': 'Total', 'Points to be Awarded': '', 'no of students': '', 'POINTS': total_points})
        overall_api = round(total_points / total_students, 2) if total_students > 0 else '#DIV/0!'
        overall_rows.append({'Range': 'OVERALL API', 'Points to be Awarded': '', 'no of students': total_students, 'POINTS': overall_api})

        df_overall = pd.DataFrame(overall_rows)
        df_overall.to_csv(os.path.join(output_dir, 'overall_api.csv'), index=False)
        print("\nSaved overall_api.csv")

    def process_all(self):
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
        data_dir = os.path.join(base, 'data', 'class_10')
        out_dir = os.path.join(base, 'output', 'class_10')
        os.makedirs(out_dir, exist_ok=True)

        all_dfs = []
        for root, _, files in os.walk(data_dir):
            for file in files:
                if file.endswith('.pdf'):
                    df = self.process_pdf(os.path.join(root, file))
                    if not df.empty:
                        all_dfs.append(df)

        if not all_dfs:
            print("No results processed.")
            return

        merged = pd.concat(all_dfs, ignore_index=True)
        simplified = self.calculate_best_of_5(merged)
        simplified.to_csv(os.path.join(out_dir, '10th_result.csv'), index=False)

        print("\nSaved 10th_result.csv")

        for code in self.subject_codes:
            self.save_subject_api(simplified, code, out_dir)

        api_summary = self.generate_api_summary(simplified)
        api_summary.to_csv(os.path.join(out_dir, 'subject_api', 'Subject_Wise_API_Summary.csv'), index=False)
        print("\nSaved Subject_Wise_API_Summary.csv")
        print(api_summary.to_string(index=False))

        # ✅ Save overall API report
        self.generate_overall_api_report(simplified, out_dir)

def main():
    analyzer = ResultAnalyzer10th()
    analyzer.process_all()

if __name__ == "__main__":
    main()
