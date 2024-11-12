from django.db import models

# Create your models here.

class Abbreviations(models.Model):
    name = models.TextField()

    class Meta:
        managed = False
        db_table = 'Abbreviations'


class Abbreviationsreg(models.Model):
    abbreviation = models.OneToOneField(Abbreviations, models.DO_NOTHING, db_column='abbreviation', primary_key=True)
    transcript = models.TextField()

    class Meta:
        managed = False
        db_table = 'AbbreviationsReg'

class Abbreviationsloc(models.Model):
    abbreviation = models.ForeignKey(Abbreviations, models.DO_NOTHING, db_column='abbreviation', blank=True, null=True)
    language = models.ForeignKey('Languages', models.DO_NOTHING, db_column='language', blank=True, null=True)
    transcript = models.TextField()

    class Meta:
        managed = False
        db_table = 'AbbreviationsLoc'

class Biologicalactivity(models.Model):
    name = models.TextField()
    rus = models.TextField()
    eng = models.TextField()
    description = models.TextField()

    class Meta:
        managed = False
        db_table = 'BiologicalActivity'


class Biologicalactivitygroups(models.Model):
    name = models.TextField()

    class Meta:
        managed = False
        db_table = 'BiologicalActivityGroups'

class Chemicalcompounds(models.Model):
    name = models.TextField()

    class Meta:
        managed = False
        db_table = 'ChemicalCompounds'

class Chemicalcompoundsgroups(models.Model):
    name = models.TextField()
    rus = models.TextField()
    eng = models.TextField()

    class Meta:
        managed = False
        db_table = 'ChemicalCompoundsGroups'

class Chemicalcompoundsdistribution(models.Model):
    # activity = models.ForeignKey(Biologicalactivitygroups, models.DO_NOTHING, db_column='activity', blank=True, null=True)
    # compound = models.ForeignKey(Chemicalcompounds, models.DO_NOTHING, db_column='compound', blank=True, null=True)
    activity = models.OneToOneField(Biologicalactivitygroups, models.DO_NOTHING, db_column='activity', primary_key=True)  # The composite primary key (activity, compound) found, that is not supported. The first column is selected.
    compound = models.ForeignKey(Chemicalcompounds, models.DO_NOTHING, db_column='compound')

    class Meta:
        managed = False
        db_table = 'ChemicalCompoundsDistribution'

class Biologicallyactivecompounds(models.Model):
    name = models.TextField()
    compounds_group = models.ForeignKey(Chemicalcompoundsgroups, models.DO_NOTHING, db_column='compounds_group', blank=True, null=True)
    compounds_group_text = models.TextField()
    note = models.TextField()
    rus = models.TextField()
    eng = models.TextField()
    see = models.ForeignKey('self', models.DO_NOTHING, db_column='see', blank=True, null=True)
    comment = models.TextField()
    rus_alt = models.TextField(blank=True, null=True)
    biological_activity_extra = models.TextField()
    chemical_compound = models.ForeignKey(Chemicalcompounds, models.DO_NOTHING, db_column='chemical_compound', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'BiologicallyActiveCompounds'

class BacBiologicalactivity(models.Model):
    bac = models.ForeignKey(Biologicallyactivecompounds, models.DO_NOTHING, db_column='bac')
    text = models.TextField()
    activity = models.ForeignKey(Biologicalactivity, models.DO_NOTHING, db_column='activity', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'BAC_BiologicalActivity'


class Families(models.Model):
    name = models.TextField()
    rus = models.TextField()
    eng = models.TextField()

    class Meta:
        managed = False
        db_table = 'Families'


class Parts(models.Model):
    rus = models.TextField()
    eng = models.TextField()

    class Meta:
        managed = False
        db_table = 'Parts'

class Spreading(models.Model):
    name = models.TextField()

    class Meta:
        managed = False
        db_table = 'Spreading'

class Plants(models.Model):
    name = models.TextField()
    rus = models.TextField()
    eng = models.TextField()
    family = models.ForeignKey(Families, models.DO_NOTHING, db_column='family', blank=True, null=True)
    spreading = models.ForeignKey(Spreading, models.DO_NOTHING, db_column='spreading', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Plants'

class PlantsOthernames(models.Model):
    plant = models.ForeignKey(Plants, models.DO_NOTHING, db_column='plant')
    name = models.TextField()

    class Meta:
        managed = False
        db_table = 'Plants_OtherNames'


class PlantsParts(models.Model):
    plant = models.ForeignKey(Plants, models.DO_NOTHING, db_column='plant')
    part = models.ForeignKey(Parts, models.DO_NOTHING, db_column='part')

    class Meta:
        managed = False
        db_table = 'Plants_Parts'

class BacPlants(models.Model):
    bac = models.ForeignKey(Biologicallyactivecompounds, models.DO_NOTHING, db_column='bac')
    plant = models.ForeignKey(Plants, models.DO_NOTHING, db_column='plant', blank=True, null=True)
    extra = models.TextField()

    class Meta:
        managed = False
        db_table = 'BAC_Plants'

class Languages(models.Model):
    name = models.TextField(blank=True, null=True)
    title = models.TextField(blank=True, null=True)
    long_title = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Languages'

class PlantsNames(models.Model):
    plant = models.ForeignKey('Plants', models.DO_NOTHING, db_column='plant', blank=True, null=True, related_name='linked_names')
    language = models.ForeignKey('Languages', models.DO_NOTHING, db_column='language', blank=True, null=True)
    name = models.TextField()

    class Meta:
        managed = False
        db_table = 'Plants_Names'
