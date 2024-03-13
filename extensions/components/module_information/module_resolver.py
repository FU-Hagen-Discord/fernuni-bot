import json

class ModuleResolver(object):
    """
    Resolves module numbers
    """
    def __init__(self, module_course_mapping_file: str):
        self.module_course_mapping_file = module_course_mapping_file
        self._module_numbers_by_course_number = {}
        self.load_mapping()

    """
    Load mapping file. Can be used to refresh the mapping on an existing ModuleResolver instance. 
    
    The expected file format looks as such:
    [
      {
        "moduleId": "69901",
        "moduleName": "Angewandte Mathematik bei Stromausfall",
        "courses": [
          {
            "courseId": "01981",
            "name": "Differentialrechnung mit dem Abakus"
          },
          {
            "courseId": "01981",
            "name": "Das sehr große Einmaleins"
          }
        ]
      },
      {
        "moduleId": "69902",
        "moduleName": "Einführung in verteiltes Echtzeit-COBOL",
        "courses": [
          {
            "courseId": "01991",
            "name": "Einführung in verteiltes Echtzeit-COBOL"
          }
        ]
      }
    ]
    """
    def load_mapping(self) -> None:
        with open(self.module_course_mapping_file, 'r') as loaded_mapping_file:
            mapping_json = json.load(loaded_mapping_file)
            for module in mapping_json:
                for course in module['courses']:
                    self._module_numbers_by_course_number.setdefault(course['courseId'], []).append(module['moduleId'])

    """
    Retrieves module ids for a course number
    
    :param int course_id: the course number
    :return: list of module ids or empty list if no modules were found
    """
    def get_modules_for_course(self, course_number: str) -> list[str]:
        return self._module_numbers_by_course_number.get(course_number, [])
