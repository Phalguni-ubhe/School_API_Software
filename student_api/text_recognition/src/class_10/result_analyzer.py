import os
import pandas as pd
import pdfplumber
import re

class ResultAnalyzer:
    def __init__(self):
        # Subject codes and names
        self.subject_codes = {
            '184': 'ENGLISH',
            '085': 'HINDI',
            '241': 'MATHEMATICS',
            '086': 'SCIENCE',
            '087': 'SOCIAL SCIENCE',
            '402': 'IT'
        }
        
        # Subject name variations for text extraction
        self.subject_names = {
            'ENGLISH': ['ENGLISH', 'ENG', 'ENGLISH LNG', 'ENGLISH LANGUAGE', 'ENGLISH LNG & LIT'],
            'HINDI': ['HINDI', 'HINDI LNG', 'HINDI LANGUAGE', 'HINDI COURSE-B'],
            'MATHEMATICS': ['MATHEMATICS', 'MATH', 'MATHS', 'MATHEMATICS BASIC'],
            'SCIENCE': ['SCIENCE', 'SCI', 'SCIENCE & TECHNOLOGY'],
            'SOCIAL SCIENCE': ['SOCIAL SCIENCE', 'SOC SCI', 'SOCIAL STUDIES', 'SST', 'SOCIAL ST', 'SOCIAL'],
            'IT': ['IT', 'INFORMATION TECHNOLOGY', 'COMPUTER', 'COMPUTERS']
        }
        
        # Grade ranges and points for API calculation
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
        
        # Columns for API table
        self.api_table_columns = [
            'SNO', 'Name of APS', 'Total Students in School as on 31 Mar 2025',
            'No of students appeared', 'No of students pass',
            '>95', '>90', '>80', '>70', '>60', '>50', '>33',
            'Compartment', 'Fail', 'API'
        ]

    def extract_text_from_pdf(self, pdf_path):
        """Extract text from PDF while preserving layout"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                print(f"\nPDF has {len(pdf.pages)} pages")
                
                for i, page in enumerate(pdf.pages):
                    print(f"\nProcessing page {i+1}...")
                    
                    # Try different extraction methods
                    page_text = page.extract_text()
                    
                    if not page_text or len(page_text.strip()) < 10:
                        words = page.extract_words()
                        page_text = ' '.join(word['text'] for word in words)
                    
                    if not page_text or len(page_text.strip()) < 10:
                        tables = page.extract_tables()
                        table_text = []
                        for table in tables:
                            for row in table:
                                table_text.extend(str(cell) for cell in row if cell)
                        page_text = ' '.join(table_text)
                    
                    text += page_text + "\n"
                    print(f"Extracted {len(page_text)} characters")
                
                return text
                
        except Exception as e:
            print(f"Error reading PDF: {str(e)}")
            return None

    def extract_student_info(self, text):
        """Extract student information from text"""
        patterns = {
            'roll_no': r'(?:Roll\s*(?:No|Number)|Seat\s*No)[.:\s]+(\d+)',
            'name': r'(?:Student|Candidate)\s*Name[.:\s]+([^\n]+)',
            'mother_name': r"(?:Mother'?s?\s*Name)[.:\s]+([^\n]+)",
            'father_name': r"(?:Father'?s?\s*Name)[.:\s]+([^\n]+)",
            'school': r"(?:School(?:'s)?\s*Name)[.:\s]+([^\n]+)",
            'division': r"Division[.:\s]+([^\n]+)",
            'result': r"Result[.:\s]+([A-Z]+)"
        }
        
        student_info = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                student_info[key] = match.group(1).strip()
        
        return student_info if len(student_info) >= 2 else None

    def extract_subject_marks(self, text):
        """Extract subject marks from text"""
        marks_data = []
        patterns = [
            r'(\d{3})\s+([A-Z][A-Z\s&\.-]+(?:LNG|STUDIES|SCIENCE|MATHEMATICS|SOCIAL|HINDI|COURSE\-B|LIT)?)\s+(\d{1,3})\s+(\d{1,3})?\s*(\d{1,3})?\s*([A-E][12])?',
            r'ADDITIONAL\s+SUBJECT\s*\n\s*INFORMATION\s*\n\s*(\d{3})\s+(\d{1,3})\s+(\d{1,3})\s+(\d{1,3})\s+([A-E][12])'
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                try:
                    if len(match.groups()) >= 3:
                        if 'ADDITIONAL' in pattern:
                            subject_code = match.group(1)
                            theory_marks = int(match.group(2))
                            practical_marks = int(match.group(3))
                            total_marks = int(match.group(4))
                            grade = match.group(5)
                            subject_name = "INFORMATION TECHNOLOGY"
                        else:
                            subject_code = match.group(1)
                            subject_name = match.group(2).strip()
                            theory_marks = int(match.group(3))
                            practical_marks = int(match.group(4)) if match.group(4) and match.group(4).strip() else 0
                            total_marks = int(match.group(5)) if match.group(5) and match.group(5).strip() else theory_marks + practical_marks
                            grade = match.group(6) if len(match.groups()) > 5 and match.group(6) else ''
                        
                        if subject_code in self.subject_codes:
                            if not any(entry['Subject Code'] == subject_code for entry in marks_data):
                                marks_data.append({
                                    'Subject Code': subject_code,
                                    'Subject': self.subject_codes[subject_code],
                                    'Theory Marks': theory_marks,
                                    'Practical Marks': practical_marks,
                                    'Total Marks': total_marks,
                                    'Grade': grade
                                })
                except Exception as e:
                    print(f"Error processing match: {e}")
                    continue
        
        return marks_data if marks_data else None

    def process_pdf_result(self, pdf_path):
        """Process a single PDF result file"""
        print(f"\nProcessing: {os.path.basename(pdf_path)}")
        
        # Extract text from PDF
        text = self.extract_text_from_pdf(pdf_path)
        if not text:
            return None
        
        # Split text into student sections
        student_sections = []
        current_section = []
        for line in text.split('\n'):
            if 'Roll No:' in line or 'Roll Number:' in line:
                if current_section:
                    student_sections.append('\n'.join(current_section))
                current_section = [line]
            else:
                current_section.append(line)
        if current_section:
            student_sections.append('\n'.join(current_section))
        
        # Process each student's section
        all_results = []
        for section in student_sections:
            student_info = self.extract_student_info(section)
            if not student_info:
                continue
            
            marks_data = self.extract_subject_marks(section)
            if not marks_data:
                continue
            
            # Add student info to each subject record
            for subject in marks_data:
                result = student_info.copy()
                result.update(subject)
                all_results.append(result)
        
        return pd.DataFrame(all_results) if all_results else None

    def create_simplified_results(self, results_df):
        """Create simplified results with specific subjects"""
        simplified_results = []
        student_groups = results_df.groupby('name')
        
        for name, group in student_groups:
            student_data = {
                'roll_no': group['roll_no'].iloc[0],
                'name': name,
                '184': 0, '085': 0, '241': 0,
                '086': 0, '087': 0, '402': 0
            }
            
            for _, row in group.iterrows():
                subject_code = row['Subject Code']
                if subject_code in student_data:
                    total_marks = row['Total Marks']
                    if total_marks > student_data[subject_code]:
                        student_data[subject_code] = total_marks
            
            # Calculate best of 5
            subject_marks = []
            for code in ['184', '085', '241', '086', '087', '402']:
                if student_data[code] > 0:
                    subject_marks.append((code, student_data[code]))
            
            subject_marks.sort(key=lambda x: x[1], reverse=True)
            best_5_subjects = subject_marks[:5]
            
            if len(best_5_subjects) >= 5:
                student_data['best_of_5'] = sum(mark for _, mark in best_5_subjects)
                student_data['percentage'] = round(student_data['best_of_5'] / 500 * 100, 2)
            else:
                student_data['best_of_5'] = 0
                student_data['percentage'] = 0
            
            simplified_results.append(student_data)
        
        return pd.DataFrame(simplified_results)

    def generate_api_table(self, results_df):
        """Generate the subject-wise API table"""
        table_data = []
        sno = 1
        
        for subject_code, subject_name in self.subject_codes.items():
            subject_marks = results_df[subject_code]
            row = {col: 0 for col in self.api_table_columns}
            
            row['SNO'] = sno
            row['Name of APS'] = ''
            row['Total Students in School as on 31 Mar 2025'] = ''
            
            total_students = len(subject_marks)
            passed_students = len(subject_marks[subject_marks >= 33])
            
            row['No of students appeared'] = total_students
            row['No of students pass'] = passed_students
            
            # Calculate mark ranges
            row['>95'] = len(subject_marks[subject_marks > 95])
            row['>90'] = len(subject_marks[(subject_marks > 90) & (subject_marks <= 95)])
            row['>80'] = len(subject_marks[(subject_marks > 80) & (subject_marks <= 90)])
            row['>70'] = len(subject_marks[(subject_marks > 70) & (subject_marks <= 80)])
            row['>60'] = len(subject_marks[(subject_marks > 60) & (subject_marks <= 70)])
            row['>50'] = len(subject_marks[(subject_marks > 50) & (subject_marks <= 60)])
            row['>33'] = len(subject_marks[(subject_marks > 33) & (subject_marks <= 50)])
            row['Compartment'] = len(subject_marks[(subject_marks > 0) & (subject_marks < 33)])
            row['Fail'] = len(subject_marks[subject_marks == 0])
            
            # Calculate API
            if total_students > 0:
                points = (
                    row['>95'] * 10 +
                    row['>90'] * 8 +
                    row['>80'] * 6 +
                    row['>70'] * 4 +
                    row['>60'] * 2 +
                    row['>50'] * 0 +
                    row['>33'] * -1 +
                    row['Compartment'] * -2 +
                    row['Fail'] * -3
                )
                row['API'] = round((points / total_students) * 100, 2)
            else:
                row['API'] = '#DIV/0!'
            
            table_data.append(row)
            sno += 1
        
        # Create DataFrame and add subject names
        table_df = pd.DataFrame(table_data)
        subject_series = pd.Series(self.subject_codes.values(), name='Subject')
        table_df = pd.concat([subject_series, table_df], axis=1)
        
        return table_df

    def save_subject_api(self, subject_code, subject_name, subject_marks, output_dir):
        """Save API calculation for a specific subject"""
        # Create distribution data
        distribution_data = []
        total_students = len(subject_marks)
        total_points = 0
        
        # Calculate distribution for each grade range
        for min_mark, max_mark, points, range_label in self.grade_ranges:
            students_in_range = len(subject_marks[(subject_marks > min_mark) & (subject_marks <= max_mark)])
            range_points = students_in_range * points
            total_points += range_points
            
            distribution_data.append({
                'Range': range_label,
                'Points to be Awarded': points,
                'no of students': students_in_range,
                'POINTS': range_points
            })
        
        # Add total row
        distribution_data.append({
            'Range': 'Total',
            'Points to be Awarded': '',
            'no of students': total_students,
            'POINTS': total_points
        })
        
        # Calculate API
        api_value = round((total_points / total_students) * 100, 2) if total_students > 0 else '#DIV/0!'
        
        # Create output directory
        subject_api_dir = os.path.join(output_dir, 'subject_api')
        os.makedirs(subject_api_dir, exist_ok=True)
        
        # Save to CSV
        output_file = os.path.join(subject_api_dir, f'API_{subject_name}.csv')
        df = pd.DataFrame(distribution_data)
        df.to_csv(output_file, index=False)
        
        # Add API value at the bottom
        with open(output_file, 'a') as f:
            f.write(f'\nAPI- {subject_name},{api_value}\n')
            f.write(f'Total Students,{total_students}\n')
        
        print(f"\nSaved API calculation for {subject_name} to {output_file}")
        print(f"API-{subject_name}: {api_value}")

    def process_all_results(self):
        """Process all results and generate reports"""
        # Get file paths
        current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        data_dir = os.path.join(current_dir, 'data', 'class_10')
        output_dir = os.path.join(current_dir, 'output', 'class_10')
        
        # Create directories if they don't exist
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
        
        # Find PDF files
        pdf_files = []
        for root, _, files in os.walk(data_dir):
            for file in files:
                if file.endswith('.pdf'):
                    pdf_files.append(os.path.join(root, file))
        
        if not pdf_files:
            print(f"No PDF files found in {data_dir}")
            return
        
        # Process each PDF file
        all_results = []
        for pdf_path in pdf_files:
            results = self.process_pdf_result(pdf_path)
            if results is not None:
                all_results.append(results)
        
        if not all_results:
            print("No results could be processed")
            return
        
        # Combine all results
        combined_results = pd.concat(all_results, ignore_index=True)
        
        # Create simplified results
        simplified_results = self.create_simplified_results(combined_results)
        simplified_path = os.path.join(output_dir, '10th_result.csv')
        simplified_results.to_csv(simplified_path, index=False)
        print(f"\nSaved marks summary to: {simplified_path}")
        
        # Generate individual subject API files
        print("\nGenerating subject-wise API files...")
        for subject_code, subject_name in self.subject_codes.items():
            subject_marks = simplified_results[subject_code]
            self.save_subject_api(subject_code, subject_name, subject_marks, output_dir)
        
        # Generate API summary table
        api_table = self.generate_api_table(simplified_results)
        api_table_path = os.path.join(output_dir, 'subject_api', 'Subject_Wise_API_Summary.csv')
        api_table.to_csv(api_table_path, index=False)
        print(f"\nSaved subject-wise API summary to: {api_table_path}")
        
        # Display results
        print("\nProcessing complete!")
        print(f"Total students processed: {len(simplified_results)}")
        print("\nSubject-wise API Summary:")
        print("-" * 100)
        print(api_table.to_string(index=False))
        print("-" * 100)

def main():
    analyzer = ResultAnalyzer()
    analyzer.process_all_results()

if __name__ == "__main__":
    main() 