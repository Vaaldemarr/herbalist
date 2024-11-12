from .models_bav import Languages, Abbreviationsloc

class ReplaceText:
    def __init__(self, language: Languages) -> None:
        self._language = language
        self._abbreviations  = {item.abbreviation: item.transcript for item in Abbreviationsloc.objects.using('bav').filter(language_id=language.id).all()}

    def replace_abbreviations(self, text: str):
        result = text
        for abbr, transcr in self._abbreviations.items():
            result = result.replace(abbr.name, transcr)
        return result

class QueryTexts:

    def __init__(self, language: Languages) -> None:
        self._language = language

    def get_query(self, title, search_str, id=None):
        if title == 'plant_bac_query':
            return self.plant_bac_query(self._language, search_str, id)
        elif title == 'plant_activity_query':
            return self.plant_activity_query(self._language, search_str, id)
        elif title == 'compounds_plant_query':
            return self.compounds_plant_query(self._language, search_str, id)
        elif title == 'compounds_activity_query':
            return self.compounds_activity_query(self._language, search_str, id)
        elif title == 'activity_bac_query':
            return self.activity_bac_query(self._language, search_str, id)
        elif title == 'activity_plant_query':
            return self.activity_plant_query(self._language, search_str, id)
        
    @staticmethod
    def plant_bac_query(lang: Languages, search_str, id):
        if lang.name == 'ru':
            result = """
                SELECT bp.bac, bp.extra
                FROM BAC_Plants AS bp
                    LEFT JOIN
                    BiologicallyActiveCompounds AS bc ON bc.id = bp.bac
                WHERE plant = %s AND 
                    (bc.rus LIKE %s OR bc.rus LIKE %s OR 
                        LOWER(bc.eng) LIKE %s );
            """
            params = [id, 
                    '%' + search_str + '%', 
                    '%' + search_str.capitalize() + '%', 
                    '%' + search_str.lower() + '%']
        else:
            result = """
                SELECT bp.bac, bp.extra
                FROM BAC_Plants AS bp
                    LEFT JOIN
                    BiologicallyActiveCompounds AS bc ON bc.id = bp.bac
                WHERE plant = %s AND 
                        LOWER(bc.eng) LIKE %s;
            """
            params = [id, 
                    '%' + search_str.lower() + '%']
            
        return result, params

    @staticmethod
    def plant_activity_query(lang: Languages, search_str, id):
        if lang.name == 'ru':
            result = """
                SELECT DISTINCT ba.activity, ba.text
                FROM BAC_Plants AS bp
                    JOIN
                    BAC_BiologicalActivity AS ba ON bp.bac = ba.bac AND bp.plant = %s
                    JOIN
                    BiologicalActivity AS ba2 ON ba.activity = ba2.id
                WHERE ba2.rus LIKE %s OR ba2.rus LIKE %s OR LOWER(ba2.eng) LIKE %s;
                """
            params = [id, 
                    '%' + search_str + '%', 
                    '%' + search_str.capitalize() + '%', 
                    '%' + search_str.lower() + '%']
        else:
            result = """
                SELECT DISTINCT ba.activity, ba.text
                FROM BAC_Plants AS bp
                    JOIN
                    BAC_BiologicalActivity AS ba ON bp.bac = ba.bac AND bp.plant = %s
                    JOIN
                    BiologicalActivity AS ba2 ON ba.activity = ba2.id
                WHERE LOWER(ba2.eng) LIKE %s;
                """
            params = [id, '%' + search_str.lower() + '%']

        return result, params

    @staticmethod
    def compounds_plant_query(lang: Languages, search_str, id):
        if lang.name == 'ru':
            result = """SELECT DISTINCT BAC_Plants.plant
            FROM BAC_Plants
                LEFT JOIN
                Plants ON BAC_Plants.plant = Plants.id
            WHERE BAC_Plants.bac = %s AND 
                (Plants.rus LIKE %s OR Plants.rus LIKE %s OR
                LOWER(Plants.eng) LIKE %s)
            """
            params = [id,
                      '%' + search_str + '%', 
                      '%' + search_str.capitalize() + '%', 
                      '%' + search_str.lower() + '%']
        else:
            result = """SELECT DISTINCT BAC_Plants.plant
            FROM BAC_Plants
                LEFT JOIN
                Plants ON BAC_Plants.plant = Plants.id
                LEFT JOIN
                Plants_Names ON BAC_Plants.plant = Plants_Names.plant AND Plants_Names.language=%s
            WHERE BAC_Plants.bac = %s AND 
                (LOWER(Plants.eng) LIKE %s OR
                LOWER(Plants_Names.name) LIKE %s)
            """
            params = [lang.id, id,
                    '%' + search_str.lower() + '%',
                    '%' + search_str.lower() + '%']

        return result, params
    

    @staticmethod
    def compounds_activity_query(lang: Languages, search_str, id):
        if lang.name == 'ru':
            result = """
            SELECT ba.activity
            FROM BAC_BiologicalActivity AS ba
                LEFT JOIN
                BiologicalActivity AS ba2 ON ba2.id = ba.activity
            WHERE ba.bac = %s AND 
                (ba2.rus LIKE %s OR ba2.rus LIKE %s OR
                LOWER(ba2.eng) LIKE %s);
            """
            params = [id,
                        '%' + search_str + '%', 
                        '%' + search_str.capitalize() + '%',
                        '%' + search_str.lower() + '%', 
                      ]
        else:
            result = """
            SELECT ba.activity
            FROM BAC_BiologicalActivity AS ba
                LEFT JOIN
                BiologicalActivity AS ba2 ON ba2.id = ba.activity
            WHERE ba.bac = %s AND 
                LOWER(ba2.eng) LIKE %s;
            """
            params = [id,
                        '%' + search_str.lower() + '%', 
                      ]

        return result, params

    @staticmethod
    def activity_bac_query(lang: Languages, search_str, id):
        result = """
        SELECT bba.bac
        FROM BAC_BiologicalActivity as bba
        LEFT JOIN BiologicallyActiveCompounds as compound ON compound.id=bba.bac
        WHERE bba.activity = %s AND"""
        if lang.name == 'ru':
            result += """
            (compound.rus LIKE %s OR compound.rus LIKE %s OR
            LOWER(compound.eng) LIKE %s)
            """
            params = [id, 
                    '%' + search_str + '%', 
                    '%' + search_str.capitalize() + '%', 
                    '%' + search_str.lower() + '%']
        else:
            result += """
            LOWER(compound.eng) LIKE %s
            """
            params = [id, 
                    '%' + search_str.lower() + '%']
            
        return result, params

    @staticmethod
    def activity_plant_query(lang: Languages, search_str, id):
        result = """
        SELECT DISTINCT BAC_Plants.plant
        FROM BAC_BiologicalActivity AS ba
            JOIN
            BAC_Plants ON ba.bac = BAC_Plants.bac
            LEFT JOIN
            Plants ON BAC_Plants.plant = Plants.id
            LEFT JOIN
            Plants_Names ON BAC_Plants.plant = Plants_Names.plant AND Plants_Names.language=1
        WHERE ba.activity = %s AND"""
        if lang.name == 'ru':
            result += """
            (Plants.rus LIKE %s OR Plants.rus LIKE %s OR
             LOWER(Plants.eng) LIKE %s)
            """
            params = [id, 
                    '%' + search_str + '%', 
                    '%' + search_str.capitalize() + '%', 
                    '%' + search_str.lower() + '%']
        else:
            result += """
            (LOWER(Plants.eng) LIKE %s OR
             LOWER(Plants_Names.name) LIKE %s)
            """
            params = [id, 
                    '%' + search_str.lower() + '%',
                    '%' + search_str.lower() + '%']
            
        return result, params
