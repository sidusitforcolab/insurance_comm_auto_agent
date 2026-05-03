"""Synthetic PDF generator for creating dummy insurance documents."""
import os
import random
from datetime import datetime, timedelta
from typing import Dict, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src.config.settings import settings


class SyntheticPDFGenerator:
    """Generate synthetic insurance documents for testing."""

    def __init__(self, output_dir: str = "data/samples"):
        """Initialize the PDF generator."""
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.styles = getSampleStyleSheet()

    def generate_mvr(self, applicant_id: str, vehicle_info: Dict = None) -> str:
        """Generate a Motor Vehicle Record (MVR) PDF."""
        if vehicle_info is None:
            vehicle_info = self._generate_random_vehicle_info()

        filename = f"{self.output_dir}/mvr_{applicant_id}.pdf"
        doc = SimpleDocTemplate(filename, pagesize=letter)
        story = []

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
        )
        story.append(Paragraph("MOTOR VEHICLE RECORD", title_style))
        story.append(Spacer(1, 12))

        # Driver Information
        story.append(Paragraph("DRIVER INFORMATION", self.styles['Heading2']))
        driver_data = [
            ["Name:", vehicle_info.get('driver_name', 'John Doe')],
            ["License Number:", vehicle_info.get('license_number', 'DL123456789')],
            ["Date of Birth:", vehicle_info.get('dob', '1985-06-15')],
            ["Address:", vehicle_info.get('address', '123 Main St, Anytown, USA')],
        ]
        driver_table = Table(driver_data, colWidths=[2*inch, 4*inch])
        driver_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(driver_table)
        story.append(Spacer(1, 12))

        # Vehicle Information
        story.append(Paragraph("VEHICLE INFORMATION", self.styles['Heading2']))
        vehicle_data = [
            ["Make/Model:", f"{vehicle_info.get('make', 'Ford')}/{vehicle_info.get('model', 'F-150')}"],
            ["Year:", str(vehicle_info.get('year', 2020))],
            ["VIN:", vehicle_info.get('vin', '1FTFW1ET5DFC12345')],
            ["Type:", vehicle_info.get('type', 'Truck')],
        ]
        vehicle_table = Table(vehicle_data, colWidths=[2*inch, 4*inch])
        vehicle_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(vehicle_table)
        story.append(Spacer(1, 12))

        # Violation History
        story.append(Paragraph("VIOLATION HISTORY (Last 3 Years)", self.styles['Heading2']))
        violations = vehicle_info.get('violations', [])
        if violations:
            violation_data = [["Date", "Violation", "Points", "Fine"]]
            for v in violations:
                violation_data.append([v['date'], v['description'], str(v['points']), f"${v['fine']}"])
            violation_table = Table(violation_data, colWidths=[1.5*inch, 2.5*inch, 1*inch, 1*inch])
            violation_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(violation_table)
        else:
            story.append(Paragraph("No violations found in the last 3 years.", self.styles['Normal']))

        doc.build(story)
        return filename

    def generate_loss_run(self, applicant_id: str, claims: List[Dict] = None) -> str:
        """Generate a Loss Run report PDF."""
        if claims is None:
            claims = self._generate_random_claims()

        filename = f"{self.output_dir}/loss_run_{applicant_id}.pdf"
        doc = SimpleDocTemplate(filename, pagesize=letter)
        story = []

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
        )
        story.append(Paragraph("LOSS RUN REPORT", title_style))
        story.append(Spacer(1, 12))

        # Company Information
        story.append(Paragraph("COMPANY INFORMATION", self.styles['Heading2']))
        company_data = [
            ["Company Name:", f"Test Company {applicant_id}"],
            ["Policy Period:", "2023-01-01 to 2023-12-31"],
            ["Report Date:", datetime.now().strftime("%Y-%m-%d")],
        ]
        company_table = Table(company_data, colWidths=[2*inch, 4*inch])
        company_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(company_table)
        story.append(Spacer(1, 12))

        # Claims History
        story.append(Paragraph("CLAIMS HISTORY", self.styles['Heading2']))
        if claims:
            claims_data = [["Date of Loss", "Claim Number", "Loss Amount", "Description"]]
            total_loss = 0
            for claim in claims:
                claims_data.append([
                    claim['date'],
                    claim['number'],
                    f"${claim['amount']:,.2f}",
                    claim['description']
                ])
                total_loss += claim['amount']

            claims_table = Table(claims_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 2.5*inch])
            claims_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(claims_table)
            story.append(Spacer(1, 12))
            story.append(Paragraph(f"Total Loss Amount: ${total_loss:,.2f}", self.styles['Heading3']))
        else:
            story.append(Paragraph("No claims found in the reporting period.", self.styles['Normal']))

        doc.build(story)
        return filename

    def generate_inspection_report(self, applicant_id: str, inspection_data: Dict = None) -> str:
        """Generate an Inspection Report PDF."""
        if inspection_data is None:
            inspection_data = self._generate_random_inspection()

        filename = f"{self.output_dir}/inspection_{applicant_id}.pdf"
        doc = SimpleDocTemplate(filename, pagesize=letter)
        story = []

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
        )
        story.append(Paragraph("VEHICLE INSPECTION REPORT", title_style))
        story.append(Spacer(1, 12))

        # Inspection Details
        story.append(Paragraph("INSPECTION DETAILS", self.styles['Heading2']))
        inspection_info = [
            ["Inspection Date:", inspection_data.get('date', datetime.now().strftime("%Y-%m-%d"))],
            ["Inspector:", inspection_data.get('inspector', 'Certified Inspector')],
            ["Location:", inspection_data.get('location', 'Service Center')],
            ["Overall Rating:", inspection_data.get('rating', 'PASS')],
        ]
        info_table = Table(inspection_info, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(info_table)
        story.append(Spacer(1, 12))

        # Inspection Items
        story.append(Paragraph("INSPECTION ITEMS", self.styles['Heading2']))
        items = inspection_data.get('items', [])
        if items:
            item_data = [["Component", "Status", "Notes"]]
            for item in items:
                status_color = colors.green if item['status'] == 'PASS' else colors.red
                item_data.append([item['component'], item['status'], item['notes']])

            item_table = Table(item_data, colWidths=[2*inch, 1*inch, 3*inch])
            item_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(item_table)

        doc.build(story)
        return filename

    def generate_policy_document(self, applicant_id: str, policy_data: Dict = None) -> str:
        """Generate a Policy Document PDF."""
        if policy_data is None:
            policy_data = self._generate_random_policy()

        filename = f"{self.output_dir}/policy_{applicant_id}.pdf"
        doc = SimpleDocTemplate(filename, pagesize=letter)
        story = []

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
        )
        story.append(Paragraph("COMMERCIAL AUTO INSURANCE POLICY", title_style))
        story.append(Spacer(1, 12))

        # Policy Information
        story.append(Paragraph("POLICY INFORMATION", self.styles['Heading2']))
        policy_info = [
            ["Policy Number:", policy_data.get('number', f"POL{applicant_id}")],
            ["Effective Date:", policy_data.get('effective_date', '2024-01-01')],
            ["Expiration Date:", policy_data.get('expiration_date', '2024-12-31')],
            ["Insured Name:", policy_data.get('insured_name', f"Test Company {applicant_id}")],
        ]
        info_table = Table(policy_info, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(info_table)
        story.append(Spacer(1, 12))

        # Coverage Details
        story.append(Paragraph("COVERAGE DETAILS", self.styles['Heading2']))
        coverage = policy_data.get('coverage', [])
        if coverage:
            coverage_data = [["Coverage Type", "Limit", "Deductible"]]
            for cov in coverage:
                coverage_data.append([cov['type'], cov['limit'], cov['deductible']])

            coverage_table = Table(coverage_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
            coverage_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(coverage_table)

        story.append(Spacer(1, 12))
        story.append(Paragraph("EXCLUSIONS AND LIMITATIONS", self.styles['Heading2']))
        exclusions = policy_data.get('exclusions', [
            "Intentional acts",
            "Nuclear energy liability",
            "War and military action",
            "Wear and tear"
        ])
        for exclusion in exclusions:
            story.append(Paragraph(f"• {exclusion}", self.styles['Normal']))

        doc.build(story)
        return filename

    def _generate_random_vehicle_info(self) -> Dict:
        """Generate random vehicle information."""
        makes = ["Ford", "Chevrolet", "Toyota", "Honda", "Dodge", "GMC"]
        models = {
            "Ford": ["F-150", "F-250", "Explorer"],
            "Chevrolet": ["Silverado", "Tahoe", "Suburban"],
            "Toyota": ["Tacoma", "Tundra", "4Runner"],
            "Honda": ["Ridgeline", "Pilot"],
            "Dodge": ["Ram", "Durango"],
            "GMC": ["Sierra", "Yukon"]
        }

        make = random.choice(makes)
        model = random.choice(models[make])
        year = random.randint(2015, 2023)

        # Generate some random violations (0-3)
        violations = []
        num_violations = random.randint(0, 3)
        violation_types = [
            {"description": "Speeding", "points": 3, "fine": 150},
            {"description": "Failure to yield", "points": 2, "fine": 100},
            {"description": "Improper lane change", "points": 2, "fine": 120},
            {"description": "Running red light", "points": 3, "fine": 200},
        ]

        for i in range(num_violations):
            violation = random.choice(violation_types).copy()
            # Random date within last 3 years
            days_ago = random.randint(0, 1095)  # 3 years
            violation_date = datetime.now() - timedelta(days=days_ago)
            violation["date"] = violation_date.strftime("%Y-%m-%d")
            violations.append(violation)

        return {
            "driver_name": f"Driver {random.randint(1, 1000)}",
            "license_number": f"DL{random.randint(100000000, 999999999)}",
            "dob": f"{random.randint(1960, 1990)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
            "address": f"{random.randint(1, 9999)} {random.choice(['Main', 'Oak', 'Pine', 'Elm'])} St, {random.choice(['Anytown', 'Springfield', 'Riverside'])}, USA",
            "make": make,
            "model": model,
            "year": year,
            "vin": f"{random.randint(1, 9)}{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=16))}",
            "type": "Truck" if "F-" in model or "Silverado" in model or "Ram" in model or "Sierra" in model else "Van",
            "violations": violations
        }

    def _generate_random_claims(self) -> List[Dict]:
        """Generate random claims data."""
        claims = []
        num_claims = random.randint(0, 5)

        claim_descriptions = [
            "Rear-end collision at intersection",
            "Side impact collision while parked",
            "Property damage from hail storm",
            "Theft of vehicle accessories",
            "Collision with deer on highway",
            "Damage from fallen tree branch",
            "Vandalism to vehicle exterior",
            "Collision during adverse weather conditions"
        ]

        for i in range(num_claims):
            days_ago = random.randint(0, 1095)  # Last 3 years
            claim_date = datetime.now() - timedelta(days=days_ago)

            claims.append({
                "date": claim_date.strftime("%Y-%m-%d"),
                "number": f"CLM{random.randint(100000, 999999)}",
                "amount": round(random.uniform(500, 25000), 2),
                "description": random.choice(claim_descriptions)
            })

        return claims

    def _generate_random_inspection(self) -> Dict:
        """Generate random inspection data."""
        components = [
            "Brakes", "Tires", "Engine", "Transmission", "Electrical System",
            "Suspension", "Steering", "Exhaust", "Lights", "Safety Equipment"
        ]

        items = []
        all_pass = random.choice([True, False])  # 50% chance of all passing

        for component in components:
            if all_pass or random.choice([True, False]):
                status = "PASS"
                notes = "No issues found"
            else:
                status = "FAIL"
                notes = f"Requires {random.choice(['repair', 'replacement', 'maintenance'])}"

            items.append({
                "component": component,
                "status": status,
                "notes": notes
            })

        overall_rating = "PASS" if all(item['status'] == 'PASS' for item in items) else "CONDITIONAL"

        return {
            "date": (datetime.now() - timedelta(days=random.randint(0, 365))).strftime("%Y-%m-%d"),
            "inspector": f"Inspector {random.choice(['Smith', 'Johnson', 'Williams', 'Brown', 'Jones'])}",
            "location": random.choice(["Downtown Service Center", "North Branch", "South Depot", "East Terminal"]),
            "rating": overall_rating,
            "items": items
        }

    def _generate_random_policy(self) -> Dict:
        """Generate random policy data."""
        coverage_types = [
            {"type": "Bodily Injury Liability", "limit": "$1,000,000/$2,000,000", "deductible": "N/A"},
            {"type": "Property Damage Liability", "limit": "$500,000", "deductible": "N/A"},
            {"type": "Uninsured Motorist", "limit": "$500,000/$1,000,000", "deductible": "N/A"},
            {"type": "Collision Coverage", "limit": "Actual Cash Value", "deductible": "$1,000"},
            {"type": "Comprehensive Coverage", "limit": "Actual Cash Value", "deductible": "$500"},
        ]

        return {
            "number": f"POL{random.randint(1000000, 9999999)}",
            "effective_date": "2024-01-01",
            "expiration_date": "2024-12-31",
            "insured_name": f"Test Company {random.randint(100, 999)}",
            "coverage": coverage_types,
            "exclusions": [
                "Intentional acts",
                "Nuclear energy liability",
                "War and military action",
                "Wear and tear",
                "Mechanical breakdown"
            ]
        }


def generate_sample_documents(num_applicants: int = 5) -> List[Dict]:
    """Generate sample documents for multiple applicants."""
    generator = SyntheticPDFGenerator()
    documents = []

    for i in range(1, num_applicants + 1):
        applicant_id = f"APP{i:03d}"

        # Generate all document types for each applicant
        mvr_file = generator.generate_mvr(applicant_id)
        loss_run_file = generator.generate_loss_run(applicant_id)
        inspection_file = generator.generate_inspection_report(applicant_id)
        policy_file = generator.generate_policy_document(applicant_id)

        documents.append({
            "applicant_id": applicant_id,
            "documents": {
                "mvr": mvr_file,
                "loss_run": loss_run_file,
                "inspection": inspection_file,
                "policy": policy_file
            }
        })

    return documents


if __name__ == "__main__":
    # Generate sample documents for testing
    docs = generate_sample_documents(5)
    print(f"Generated {len(docs)} sets of sample documents:")
    for doc_set in docs:
        print(f"Applicant {doc_set['applicant_id']}:")
        for doc_type, filepath in doc_set['documents'].items():
            print(f"  {doc_type}: {filepath}")