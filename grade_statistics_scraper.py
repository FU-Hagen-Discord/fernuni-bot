import asyncio
import httpx
from bs4 import BeautifulSoup, ResultSet
from dotenv import load_dotenv
from models import ExtractedGradeStatistics, UniversityModule, ModuleGradeStatistics
from itertools import groupby
import logging

class GradeStatisticsScraper:
    # URL to scrape grade statistics from
    URL = "https://www.fernuni-hagen.de/wirtschaftswissenschaft/studium/klausurstatistik.shtml"

    def __init__(self):
        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
        self.logger = logging.getLogger(__name__)

    async def download_page(self) -> ResultSet:
        """
        Download the statistics page and return all relevant HTML elements.
        Returns a list of h2, h3, and table elements.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(self.URL)
            response.encoding = "utf-8"
            soup = BeautifulSoup(response.text, "html.parser")
            return soup.find_all(["h2", "h3", "table"])
        
    @staticmethod
    def extract_modules(extracted_grade_statistics: list[ExtractedGradeStatistics]) -> list[UniversityModule]:
        sorted_grade_statistics = extracted_grade_statistics.copy()
        sorted_grade_statistics.sort(key=lambda x: (x.module_number, x.year, x.is_summer_semester, x.examination_period))

        modules = list()

        for module_number,statistics in groupby(sorted_grade_statistics, key=lambda x: x.module_number):
            statistics_list = list(statistics)
            latest_statistic = statistics_list[-1]
            
            new_module: UniversityModule = UniversityModule()
            new_module.number = int(latest_statistic.module_number)
            new_module.title = latest_statistic.module_name

            modules.append(new_module)

        return modules
        
    async def get_module_changes(self, modules: list[UniversityModule]) -> dict:
        """
        Compare extracted modules with database entries and determine which modules are new or have changed.
        Returns a dictionary with lists of new and changed modules.
        """
        change_container = {
            "new_modules": [],
            "changed_modules": []
        }
        
        for module in modules:
            existing_module = None
            try:
                existing_module = UniversityModule.get_or_none(number=module.number)
            except Exception as e:
                self.logger.error(f"Error checking module {module.number}: {e}")
                continue
                
            if not existing_module:
                change_container["new_modules"].append(module)
                continue
                
            # Check if title has changed
            if existing_module.title != module.title:
                change_container["changed_modules"].append({
                    "existing": existing_module,
                    "updated": module
                })
                
        return change_container
        
    async def store_module_changes(self, changes: dict) -> None:
        """
        Save new and changed modules to the database.
        Args:
            changes: Dictionary containing lists of new and changed modules
        """
        # Store new modules
        for module in changes["new_modules"]:
            try:
                with UniversityModule._meta.database.atomic() as txn:
                    UniversityModule.create(
                        number=module.number,
                        title=module.title
                    )
                    self.logger.info(f"Added new module: {module.number} - {module.title}")
                    txn.commit()
            except Exception as e:
                self.logger.error(f"Error adding module {module.number}: {e}")
                
        # Update changed modules
        for change in changes["changed_modules"]:
            existing = change["existing"]
            updated = change["updated"]
            try:
                with UniversityModule._meta.database.atomic() as txn:
                    existing.title = updated.title
                    existing.save()
                    self.logger.info(f"Updated module: {existing.number} - {existing.title}")
                    txn.commit()
            except Exception as e:
                self.logger.error(f"Error updating module {existing.number}: {e}")

                

    async def extract_grade_statistics(self, page_content: ResultSet) -> list[ExtractedGradeStatistics]:
        """
        Parse the HTML content and extract all module statistics.
        Returns a list of GradeStatistics objects.
        """
        extracted_grade_statistics: list[ExtractedGradeStatistics] = []
        year = 0
        examination_period = "Unknown"
        is_summer_semester = False

        # Iterate over all elements (headers and tables)
        for element in page_content:
            if element.name in ["h2", "h3"]:
                # Parse semester header to get year, semester type, and period
                current_semester: str = element.get_text(strip=True)
                for semester_part in current_semester.lower().split(" "):
                    has_slash = semester_part.count("/") > 0
                    if has_slash:
                        years = semester_part.split("/")
                        if len(years) == 2 and years[0].isdigit() and years[1].isdigit():
                            year = int(years[0])
                            year += 1
                            is_summer_semester = False
                    elif semester_part.isdigit():
                        year = int(semester_part)
                    elif "sommer" in semester_part:
                        is_summer_semester = True
                    elif "winter" in semester_part:
                        is_summer_semester = False
                    elif semester_part.startswith("p"):
                        examination_period = semester_part.upper()
            elif element.name == "table":
                # Parse table rows for module statistics
                rows = element.find_all("tr")
                if len(rows) != 3:
                    self.logger.info(f"Something is off with the table for {current_semester}, it has {len(rows)} rows.")
                    continue
                row_1 = [col.get_text(strip=True) for col in rows[0].find_all(["th", "td"])]
                row_3 = [col.get_text(strip=True) for col in rows[2].find_all(["th", "td"])]
                module_number: str = row_1[0].strip()
                module_name: str = row_1[1].strip()
                new_extracted = ExtractedGradeStatistics(
                    module_number=int(module_number),
                    module_name=module_name,
                    is_summer_semester=is_summer_semester,
                    year=year,
                    examination_period=examination_period
                )
                # Parse grades and participants
                module_participants = 0
                module_very_good = 0
                module_good = 0
                module_satisfactory = 0
                module_sufficient = 0
                module_insufficient_grade = 0
                try:

                    if "Datenschutz" in row_3[1].strip():
                        self.logger.info(f"Data privacy notice found for module {module_number} - {module_name} in semester {year} ({'SS' if is_summer_semester else 'WS'}) - {examination_period}. Marking as anonymous.")  
                    else:
                        if row_3[0].strip().isnumeric():
                            module_participants = int(row_3[0].strip())
                        if row_3[1].strip().isnumeric():
                            module_very_good = int(row_3[1].strip())                    
                        if row_3[2].strip().isnumeric():
                            module_good = int(row_3[2].strip())
                        if row_3[3].strip().isnumeric():
                            module_satisfactory = int(row_3[3].strip())
                        if row_3[4].strip().isnumeric():
                            module_sufficient = int(row_3[4].strip())
                        if row_3[5].strip().isnumeric():
                            module_insufficient_grade = int(row_3[5].strip())
                except Exception:
                    self.logger.info(f"Error parsing numbers for module {module_number} - {module_name} in semester {year} ({'SS' if is_summer_semester else 'WS'}) - {examination_period}. Skipping this module.")
                    new_extracted.anonyomous = True
                # Assign grades to module
                new_extracted.very_good = module_very_good
                new_extracted.good = module_good
                new_extracted.satisfactory = module_satisfactory
                new_extracted.sufficient = module_sufficient
                new_extracted.insufficient = module_insufficient_grade
                # Skip modules with zero participants
                # if new_extracted.get_participant_count() == 0 and module_participants == 0: 
                #     self.logger.info(f"Skipping: Module {module_number} - {module_name} for semester {year} ({'SS' if is_summer_semester else 'WS'}) - {examination_period} has zero participants.")
                #     continue
                extracted_grade_statistics.append(new_extracted)
                self.logger.info(f"Added module: {module_number} - {module_name} for semester {year} ({'SS' if is_summer_semester else 'WS'}) - {examination_period} with {module_participants} participants.")
                self.logger.info(f"Grades: Very Good: {module_very_good}, Good: {module_good}, Satisfactory: {module_satisfactory}, Sufficient: {module_sufficient}, Insufficient: {module_insufficient_grade}")
        return extracted_grade_statistics

    async def get_changes_for_grade_statistics(self, modules: list[ExtractedGradeStatistics]) -> dict:
        """
        Compare extracted modules with database entries and determine which modules are new or have changed grades.
        Returns a dictionary with lists of added and changed modules.
        """
        change_container = {
            "added_modules": [],
            "changed_modules": []
        }
        for changed_module in modules:
            existing_study_module: ModuleGradeStatistics = None
            # Check if module already exists in the database
            try:
                existing_study_module = ModuleGradeStatistics.get_or_none(
                    module_number=changed_module.module_number,
                    is_summer_semester=changed_module.is_summer_semester,
                    examination_period=changed_module.examination_period,
                    year=changed_module.year
                )
            except Exception:
                existing_study_module = None
            # If it doesn't exist, add to added_modules
            if not existing_study_module:
                change_container["added_modules"].append({
                    "module_number": int(changed_module.module_number),
                    "module_name": changed_module.module_name,
                    "is_summer_semester": changed_module.is_summer_semester,
                    "year": changed_module.year,
                    "examination_period": changed_module.examination_period,
                    "anonymous": getattr(changed_module, "anonyomous", False),
                    "very_good": changed_module.very_good,
                    "good": changed_module.good,
                    "satisfactory": changed_module.satisfactory,
                    "sufficient": changed_module.sufficient,
                    "insufficient": changed_module.insufficient
                })
                continue
            # If it exists, check if any grades have changed
            has_module_changed = (
                existing_study_module.very_good != changed_module.very_good or
                existing_study_module.good != changed_module.good or
                existing_study_module.satisfactory != changed_module.satisfactory or
                existing_study_module.sufficient != changed_module.sufficient or
                existing_study_module.insufficient != changed_module.insufficient
            )
            if has_module_changed:
                change_container["changed_modules"].append({
                    "existing": existing_study_module,
                    "new_grades": {
                        "very_good": changed_module.very_good,
                        "good": changed_module.good,
                        "satisfactory": changed_module.satisfactory,
                        "sufficient": changed_module.sufficient,
                        "insufficient": changed_module.insufficient
                    }
                })
        return change_container

    async def store_added_grade_statistics(self, added: list[ExtractedGradeStatistics]) -> None:
        """
        Add new modules to the database.
        Each module in the list is inserted as a new record.
        """
        for module in added:
            try:
                with ModuleGradeStatistics._meta.database.atomic() as txn:
                    ModuleGradeStatistics.create(
                        module_number=int(module["module_number"]),
                        module_name=module["module_name"],
                        is_summer_semester=module["is_summer_semester"],
                        year=module["year"],
                        examination_period=module["examination_period"],
                        anonymous=module.get("anonymous", False),
                        very_good=module["very_good"],
                        good=module["good"],
                        satisfactory=module["satisfactory"],
                        sufficient=module["sufficient"],
                        insufficient=module["insufficient"]
                    )
                    txn.commit()
            except Exception as e:
                self.logger.info(f"Error adding module {module['module_number']} - {module['module_name']}: {e}")

    async def update_changed_grade_statistics(self, updated: list[ExtractedGradeStatistics]):
        """
        Update existing modules in the database with new grade values.
        Each module in the list is updated if grades have changed.
        """
        for module_change in updated:
            existing: ExtractedGradeStatistics = module_change["existing"]
            new_grades = module_change["new_grades"]
            try:
                with ModuleGradeStatistics._meta.database.atomic() as txn:
                    existing_study_module = ModuleGradeStatistics.get_or_none(
                        module_number=existing.module_number,
                        is_summer_semester=existing.is_summer_semester,
                        examination_period=existing.examination_period,
                        year=existing.year
                    )
                    existing_study_module.very_good = new_grades["very_good"]
                    existing_study_module.good = new_grades["good"]
                    existing_study_module.satisfactory = new_grades["satisfactory"]
                    existing_study_module.sufficient = new_grades["sufficient"]
                    existing_study_module.insufficient = new_grades["insufficient"]
                    existing_study_module.save()
                    txn.commit()
            except Exception as e:
                self.logger.info(f"Error updating module {existing.module_number} - {existing.module_name}: {e}")

    async def run(self):
        """
        Main entry point for scraping and syncing grade statistics.
        Downloads, parses, and updates the database as needed.
        """
        self.logger.info("Starting WiWi Scraper...")

        self.logger.info("Downloading page...")
        page_content = await self.download_page()
        self.logger.info("Extracting modules...")

        grade_statistics = await self.extract_grade_statistics(page_content)

        modules = GradeStatisticsScraper.extract_modules(grade_statistics)
        self.logger.info(f"Total modules found: {len(grade_statistics)}")

        # Process module changes first
        module_changes = await self.get_module_changes(modules)
        self.logger.info(f"New modules to add: {len(module_changes['new_modules'])}")
        self.logger.info(f"Modules to update: {len(module_changes['changed_modules'])}")

        self.logger.info("Storing module changes to database...")
        await self.store_module_changes(module_changes)
        self.logger.info("Module changes saved.")

        # Process grade statistics changes
        change_container = await self.get_changes_for_grade_statistics(grade_statistics)
        self.logger.info(f"Grade statistics to add: {len(change_container['added_modules'])}")
        self.logger.info(f"Grade statistics to update: {len(change_container['changed_modules'])}")

        self.logger.info("Storing grade statistics changes to database...")
        await self.store_added_grade_statistics(change_container["added_modules"])
        self.logger.info("Added new grade statistics.")

        await self.update_changed_grade_statistics(change_container["changed_modules"])
        self.logger.info("Updated existing modules.")
        
        self.logger.info("Done.")

if __name__ == "__main__":
    load_dotenv()
    scraper = GradeStatisticsScraper()
    asyncio.run(scraper.run())