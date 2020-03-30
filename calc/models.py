from django.db import models
from polymorphic.models import PolymorphicModel
from polymorphic.managers import PolymorphicManager
from django.urls import reverse
from django.utils.translation import gettext as _
from polymorphic.managers import PolymorphicManager, PolymorphicQuerySet
from fractions import Fraction
from functools import reduce
import math
from django.db.models import Count



from django.contrib.auth.models import User
def NON_POLYMORPHIC_CASCADE(collector, field, sub_objs, using):
    return models.CASCADE(collector, field, sub_objs.non_polymorphic(), using)

class CascadeDeletePolymorphicQuerySet(PolymorphicQuerySet):
    """
    Patch the QuerySet to call delete on the non_polymorphic QuerySet, avoiding models.deletion.Collector typing problem

    Based on workarounds proposed in: https://github.com/django-polymorphic/django-polymorphic/issues/229
    See also: https://github.com/django-polymorphic/django-polymorphic/issues/34,
              https://github.com/django-polymorphic/django-polymorphic/issues/84
    Related Django ticket: https://code.djangoproject.com/ticket/23076
    """
    def delete(self):
        if not self.polymorphic_disabled:
            return self.non_polymorphic().delete()
        else:
            return super().delete()


class CascadeDeletePolymorphicManager(PolymorphicManager):
    queryset_class = CascadeDeletePolymorphicQuerySet

class Person(PolymorphicModel):
    non_polymorphic = CascadeDeletePolymorphicManager()

    class Meta:
        base_manager_name = 'non_polymorphic'
    """Person Class"""
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
    )
    sex = models.CharField(max_length=1, choices=GENDER_CHOICES,null=False,blank=True)
    first_name = models.CharField(max_length=200,blank=True)
    last_name = models.CharField(max_length=200,blank=True)
    parents = models.ForeignKey('Marriage',null=True, on_delete=models.SET_NULL, blank=True)

    def add_father(self, father):
        if self.parents and self.parents.male:
            raise _("father already exist")
        else:
            #check for parents
            if self.parents is None:
                self.parents = Marriage.objects.create()

            self.parents.add_male(father)
            self.save()

            return father
    def add_mother(self, mother):
        if self.parents and self.parents.female:
            raise _("Mother already exist")
        else:
            #check for parents
            if self.parents is None:
                self.parents = Marriage.objects.create()

            self.parents.add_female(mother)
            self.save()
            return mother

    def add_husband(self, husband):
        #check for existing marriages
        if self.male.count() == 0:
            m = Marriage.objects.create()
            m.add_male(husband)
            m.add_female(self)
            return m
        else:
             raise _("Husband already exist")

    def add_wife(self, wife):
        #check for existing marriages
        if self.female.count() < 4:
            m = Marriage.objects.create()
            m.add_male(self)
            m.add_female(wife)
            return m
        else:
            raise _("Cann't have more than 4 wifes")

    def add_daughter(self, daughter, mother, father):

        #check if person is a male
        if self.sex == 'M':
            #check for marriages
            if self.male.count() != 0:
                daughter.parents=Marriage.objects.get(male=self, female=mother)
            else:
                daughter.parents=Marriage.objects.create()
                daughter.parents.add_male(self)
                daughter.parents.add_female(mother)

        elif self.sex == 'F':
            if self.female.count() != 0:
                daughter.parents=Marriage.objects.get(female=self, male=father)
            else:
                daughter.parents=Marriage.objects.create()
                daughter.parents.add_male(father)
                daughter.parents.add_female(self)

    def add_son(self, son, mother, father):

        #check if person is a male
        if self.sex == 'M':
            #check for marriages
            if self.male.count() != 0:
                son.parents=Marriage.objects.get(male=self, female=mother)
            else:
                son.parents=Marriage.objects.create()
                son.parents.add_male(self)
                son.parents.add_female(mother)

        elif self.sex == 'F':
            if self.female.count() != 0:
                son.parents=Marriage.objects.get(female=self, male=father)
            else:
                son.parents=Marriage.objects.create()
                son.parents.add_male(father)
                son.parents.add_female(self)

    def __str__(self):
        return f"{self.first_name} id: {self.id}"

class Marriage(models.Model):
    """Marriage Class"""
    male = models.ForeignKey(Person,null=True, on_delete=models.CASCADE,related_name='male',blank=True)
    female = models.ForeignKey(Person,null=True, on_delete=models.CASCADE,related_name='female',blank=True)

    def add_male(self, person):
        self.male = person
        self.save()

    def add_female(self, person):
        self.female = person
        self.save()

    def __str__(self):
        return "id: " + str(self.id) + " " +(self.male.first_name if self.male  else "") + " " + (self.female.first_name if self.female else "")


class Calculation(models.Model):
    """Calculation for bequest class"""
    shares = models.IntegerField(default=0)      # LCM for all prescribed shares
    excess = models.BooleanField(default=False)       # if prescribed shares is greater than gcm
    shortage = models.BooleanField(default=False)
    residual_shares = models.IntegerField(default=0)
    correction = models.BooleanField(default=False)  # shares and heirs number division should give no fractions
    shortage_calc = models.BooleanField(default=False)
    shortage_calc_shares = models.IntegerField(default=0)
    shortage_union_shares = models.IntegerField(default=0)
    shares_excess = models.IntegerField(default=0)
    shares_corrected = models.IntegerField(default=0)
    shares_shorted = models.IntegerField(default=0)

    user = models.ForeignKey(User,on_delete=models.CASCADE,null=True)
    name = models.CharField(max_length=200)

    def add_father(self, father):
        return Father().add(calc=self, father=father)

    def add_mother(self, mother):
        return Mother().add(calc=self, mother=mother)

    def add_husband(self, husband):
        return Husband().add(calc=self, husband=husband)

    def add_wife(self, wife):
        return Wife().add(calc=self, wife=wife)

    def add_daughter(self, daughter, mother, father):
        return Daughter().add(calc=self, daughter=daughter,mother=mother, father=father)

    def add_son(self, son, mother, father):
        return Son().add(calc=self, son=son, mother=mother, father=father)

    def __str__(self):
        return str(self.name)

    def get_quotes(self):
        for heir in self.heir_set.all():
            heir.get_quote(self)

    def lcm(self, a, b):
        return abs(a*b) // math.gcd(a, b)

    def lcm_list(self, list):
        return reduce(lambda a, b : self.lcm(a, b), list)

    def has_descendent(self):
        return self.heir_set.instance_of(Son).count() > 0 or self.heir_set.instance_of(Daughter).count() > 0 or self.heir_set.instance_of(SonOfSon).count() > 0 or self.heir_set.instance_of(DaughterOfSon).count() > 0

    def has_male_descendent(self):
        return self.heir_set.instance_of(Son).count() > 0 or self.heir_set.instance_of(SonOfSon).count() > 0

    def has_female_descendent(self):
        return self.heir_set.instance_of(Daughter).count() > 0 or self.heir_set.instance_of(DaughterOfSon).count() > 0

    def has_siblings(self):
        return self.heir_set.instance_of(Brother).count() + self.heir_set.instance_of(PaternalHalfBrother).count() + self.heir_set.instance_of(MaternalHalfBrother).count() + self.heir_set.instance_of(Sister).count() + self.heir_set.instance_of(PaternalHalfSister).count() + self.heir_set.instance_of(MaternalHalfSister).count() > 1

    def has_spouse(self):
        return self.heir_set.instance_of(Wife, Husband).count() > 0

    def has_asaba(self):
        return self.heir_set.filter(asaba=True).count() > 0

    def has_father(self):
        return self.heir_set.instance_of(Father).count() > 0

    def has_son(self):
        return self.heir_set.instance_of(Son).count() > 0

    def get_father(self):
        return self.heir_set.instance_of(Father).first()

    def get_mother(self):
        return self.heir_set.instance_of(Mother).first()

    def get_husband(self):
        return self.heir_set.instance_of(Husband).first()

    def get_wives(self):
        return self.heir_set.instance_of(Wife)

    def get_spouse(self):
        return self.heir_set.instance_of(Husband,Wife)

    def get_daughters(self):
        return self.heir_set.instance_of(Daughter)

    def get_sons(self):
        return self.heir_set.instance_of(Son)

    def get_heirs_no_spouse(self):
        return self.heir_set.not_instance_of(Husband, Wife)

    def get_fractions(self, heirs):
        fractions = set()
        for heir in heirs:
            fractions.add(heir.get_fraction())
        return fractions

    def set_calc_shares(self):
        count = self.heir_set.all().count()
        #if all are asaba (agnates)
        if self.heir_set.filter(asaba=True).count() == count:
            males = self.heir_set.filter(sex='M').count()
            females = self.heir_set.filter(sex='F').count()
            #if all same gender
            if   males == count or females  == count:
                self.shares = count
            else:
                for heir in self.heir_set.all():
                    self.shares = males * 2 + females
        else:
            denom_list = []
            fractions_set = self.get_fractions(self.heir_set.all())
            for fraction in fractions_set:
                denom_list.append(fraction.denominator)
            self.shares = self.lcm_list(denom_list)
        self.save()
        return self.shares
    def get_shares(self):
        shares = 0
        for  heir in self.heir_set.filter(correction=False, asaba=False):
            shares = shares + heir.share
        if self.correction == True:
            correction_set = self.heir_set.filter(correction=True, asaba=False).values('polymorphic_ctype_id','share').annotate(total=Count('id'))
            for result in correction_set:
                shares = shares + result["share"]
        asaba = self.heir_set.filter(asaba=True, correction=True).first()
        if asaba:
            shares = shares + asaba.share
        else:
            for asaba in self.heir_set.filter(asaba=True, correction=False):
                shares = shares + asaba.share
        if shares > self.shares:
            self.excess = True
            self.shares_excess = shares
            self.save()
            return self.shares_excess

        return shares

    def set_shares(self):
        for heir in self.heir_set.all():
            heir.set_share(self)

    def set_calc_correction(self):
        if self.correction == True:
            shares = 0
            if self.excess == True:
                shares = self.shares_excess
            elif self.shortage == True:
                shares = self.shares_shorted
            else:
                shares = self.shares
            correction_set = self.heir_set.filter(correction=True).values('polymorphic_ctype_id','quote').annotate(total=Count('id'))
            asaba_set = self.heir_set.filter(asaba=True, correction=True).values('polymorphic_ctype_id','quote').annotate(total=Count('id'))

            if correction_set.count() == 1:
                heir_share = self.heir_set.filter(correction=True).first().share
                count = self.heir_set.filter(correction=True).count()
                if count % heir_share == 0:
                    self.shares_corrected = math.gcd(count, heir_share) * shares
                else:
                    self.shares_corrected = count * shares
            elif asaba_set.count() == 2:
                factors = set()
                correction_set_without_asaba = self.heir_set.filter(correction=True, asaba=False).values('polymorphic_ctype_id','quote').annotate(total=Count('id'))
                males = self.heir_set.filter(asaba=True, sex='M').count()
                females = self.heir_set.filter(asaba=True, sex='F').count()
                asaba_count = males * 2 + females
                asaba_share = self.heir_set.filter(asaba=True).first().share
                if asaba_share != 0:
                    if asaba_share % asaba_count == 0:
                        factors.add(math.gcd(asaba_count, asaba_share))
                    else:
                        factors.add(asaba_count)
                for result in correction_set_without_asaba:
                    heir_share = Fraction(result["quote"]).limit_denominator().numerator
                    count = result["total"]
                    if heir_share != 0:
                        if heir_share % count == 0:
                            factors.add(math.gcd(count, heir_share))
                        else:
                            factors.add(count)
                self.shares_corrected = reduce((lambda x, y: x * y), factors) * shares
            else:
                factors = set()
                for result in correction_set:
                    heir_share = Fraction(result["quote"]).limit_denominator().numerator
                    count = result["total"]
                    if heir_share != 0:
                        if heir_share % count == 0:
                            factors.add(math.gcd(count, heir_share))
                        else:
                            factors.add(count)
                self.shares_corrected = reduce((lambda x, y: x * y), factors) * shares


            self.save()
            return self.shares_corrected

    def get_corrected_shares(self):
        if self.correction == True and self.shares_corrected != 0:
            shares = 0
            for  heir in self.heir_set.all():
                shares = shares + heir.get_corrected_share(self)
            return shares

    def set_calc_shortage(self):
        shares = self.get_shares()
        if self.shares > shares:
            self.shortage = True
            remainder = self.shares - shares
            if self.has_spouse() == False:
                self.shares_shorted = shares
                self.save()
            elif self.has_spouse() == True:
                spouse = self.get_spouse().first()
                self.shares_shorted = spouse.get_fraction().denominator
                self.save()

    def set_asaba_quotes(self):
        #check for asaba exclude father with quote
        asaba = self.heir_set.filter(asaba=True).exclude(quote__gt=0)
        count = asaba.count()
        # if no asaba then we have resedual shares to be redistributed
        if count == 0:
            pass
        for heir in asaba:
            heir.set_asaba_quote(self)

    def set_amounts(self):
        for heir in self.heir_set.all():
            heir.set_amount(self)

    def set_asaba_shares(self):
        for heir in self.heir_set.all():
            heir.set_asaba_share(self)

    def set_remainder(self):
        shares = self.get_shares()
        self.residual_shares=  self.shares - shares
        return self.residual_shares

    def set_calc_excess(self):
        shares = self.get_shares()
        if shares > self.shares:
            self.excess = True
            self.shares_excess = shares
            self.save()

    def set_shortage_shares(self):
        if self.shortage == True:
            spouse_set =  self.get_spouse()
            for spouse in spouse_set:
                spouse.shorted_share = spouse.get_fraction().numerator
                spouse.save()
            for heir in self.heir_set.not_instance_of(Husband,Wife):
                heir.set_shortage_share(self)

    def set_shortage_calc_shares(self):
        if self.shortage_calc == True:
            denom_list = []
            heirs = self.get_heirs_no_spouse()
            fractions_set = self.get_fractions(heirs)
            for fraction in fractions_set:
                denom_list.append(fraction.denominator)
            self.shortage_calc_shares = self.lcm_list(denom_list)
            self.save()

    def set_shortage_calc_share(self):
        if self.shortage_calc == True:
            heirs = self.get_heirs_no_spouse()
            for heir in heirs:
                heir.set_shortage_calc_share(self)

    def set_shortage_union_shares(self):
        if self.shortage_calc == True:
            heirs = self.get_heirs_no_spouse()
            shorted_shares = 0
            remainder = heirs.first().shorted_share
            for heir in heirs:
                shorted_shares = shorted_shares + heir.shortage_calc_share
            if shorted_shares % remainder == 0:
                self.shortage_union_shares = self.shortage_calc_shares
            else:
                self.shortage_union_shares = shorted_shares * self.shares_shorted
            self.save()
    def set_shortage_union_share(self):
        if self.shortage_calc == True:
            spouse_set =  self.get_spouse()
            multiplier = self.shortage_union_shares // self.shares_shorted
            for spouse in spouse_set:
                spouse.shortage_union_share = spouse.shorted_share * multiplier
                spouse.save()
            heirs = self.get_heirs_no_spouse()
            for heir in heirs:
                heir.set_shortage_union_share(self)

    def clear(self):
        self.shares = 0
        self.excess = False
        self.shortage = False
        self.correction = False
        self.shares_excess = 0
        self.shares_corrected = 0
        self.shares_shorted = 0
        self.save()
        for heir in self.heir_set.all():
            heir.clear()

    def compute(self):
        self.clear()
        self.get_quotes()
        self.set_calc_shares()
        self.set_shares()
        self.set_remainder()
        self.set_asaba_quotes()
        self.set_asaba_shares()
        self.get_shares()
        self.set_calc_excess()
        self.set_calc_shortage()
        self.set_shortage_shares()
        if self.shortage_calc:
            self.set_shortage_calc_shares()
            self.set_shortage_calc_share()
            self.set_shortage_union_shares()
            self.set_shortage_union_share()
        self.set_calc_correction()
        self.get_corrected_shares()
        self.set_amounts()

    def get_absolute_url(self):
        return reverse('calc:detail', args=[self.id])
class Deceased(Person):
    """Deceased class"""
    estate = models.IntegerField()
    calc = models.ForeignKey(Calculation, on_delete=NON_POLYMORPHIC_CASCADE,null=True)
    def get_absolute_url(self):
        return reverse('calc:detail', args=[self.calc.id])
class Heir(Person):
    """Heir class"""
    quote = models.DecimalField(max_digits=11, decimal_places=10, default=0)  #prescribed share
    shared_quote = models.BooleanField(default=False)    #prescribed share is shared with other heir like 2 daughters
    share = models.IntegerField(default=0)
    corrected_share = models.IntegerField(default=0)
    shorted_share = models.IntegerField(default=0)
    amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    asaba = models.BooleanField(default=False)           #agnate or residuary
    blocked = models.BooleanField(default=False)         # restrcited from inheritance
    quote_reason = models.CharField(max_length=255, default="")
    correction = models.BooleanField(default=False)
    shortage_calc = models.BooleanField(default = False)
    shortage_calc_share = models.IntegerField(default=0)
    shortage_union_share = models.IntegerField(default=0)
    abstract = True
    calc = models.ForeignKey(Calculation, on_delete=NON_POLYMORPHIC_CASCADE,null=True)
    def get_absolute_url(self):
        return reverse('calc:detail', args=[self.calc.id])
    def __str__(self):
        return (self.first_name if self.first_name else " ")
    def get_quote(self, calc):
        pass
    def set_share(self, calc):
        if self.quote != 0 and self.asaba == False:
            share = calc.shares * self.get_fraction().numerator // self.get_fraction().denominator
            if self.shared_quote == True:
                count = calc.heir_set.filter(polymorphic_ctype_id=self.polymorphic_ctype_id).count()
                if share % count == 0:
                    self.share = share // count
                    self.save()
                else:
                    self.correction=True
                    calc.correction=True
                    self.share = share
                    self.save()
                    calc.save()
            else:
                self.share=share
                self.save()
            return self.share
        else:
            return 0
    def set_shortage_share(self, calc):
        if calc.shortage == True:
            if calc.has_spouse():
                spouse = calc.get_spouse().first()
                remainder = calc.shares_shorted - spouse.shorted_share
                shorted_types = calc.heir_set.not_instance_of(Husband, Wife).values('polymorphic_ctype_id','share').annotate(total=Count('id'))
                if shorted_types.count() == 1:
                    if self.shared_quote == True:
                        count = calc.heir_set.filter(polymorphic_ctype_id=self.polymorphic_ctype_id).count()
                        if remainder % count == 0:
                            self.shorted_share = remainder // count
                        else:
                            self.correction=True
                            calc.correction=True
                            self.shorted_share = remainder
                            calc.save()
                    else :
                        self.shorted_share = remainder
                elif shorted_types.count() > 1:
                    self.shorted_share = remainder
                    self.shortage_calc = True
                    calc.shortage_calc = True
                    calc.save()
            else:
                self.shorted_share = self.share
        self.save()
        return self.shorted_share
    def set_shortage_calc_share(self, calc):
        if self.shortage_calc == True:
            share = calc.shortage_calc_shares * self.get_fraction().numerator // self.get_fraction().denominator
            if self.shared_quote == True:
                count = calc.heir_set.filter(polymorphic_ctype_id=self.polymorphic_ctype_id).count()
                if share % count == 0:
                    self.shortage_calc_share = share // count
                    self.save()
                else:
                    self.correction=True
                    calc.correction=True
                    self.share = share
                    self.save()
                    calc.save()
            else:
                self.shortage_calc_share=share
                self.save()
            return self.shortage_calc_share
    def set_shortage_union_share(self, calc):
            self.shortage_union_share = self.shortage_calc_share * self.shorted_share
            self.save()

    def set_asaba_share(self,calc):
        if self.asaba == True:
            shares = calc.shares
            remainder = calc.residual_shares
            asaba_count = calc.heir_set.filter(asaba=True).count()
            if asaba_count == 1:
                self.share = remainder
            else:
                #check for correction
                males = calc.heir_set.filter(asaba=True, sex='M').count()
                females = calc.heir_set.filter(asaba=True, sex='F').count()
                if remainder % (males*2+females) == 0:
                    if males == asaba_count or females == asaba_count:
                        self.share = remainder // asaba_count
                    else:
                        if self.sex == "M":
                            self.share = remainder // (2 * males + females) * 2
                        else:
                            self.share = remainder // (2 * males + females)
                else:
                    self.share= remainder
                    self.correction = True
            self.save()
            return self.share

    def set_asaba_quote(self, calc):
        remainder = calc.residual_shares
        shares =  calc.shares
        if remainder > 0 and shares > 0:
            if self.quote == 0:
                quote = remainder / calc.shares
                self.quote = quote
                self.quote_reason = _("residuary for asaba")
                self.save()
            else:
                quote = (remainder + self.share )/calc.shares
                self.quote = quote
                self.save()

    def get_corrected_share(self, calc):
        correction_set = calc.heir_set.filter(correction=True).values('polymorphic_ctype_id','quote').annotate(total=Count('id'))
        asaba_set = calc.heir_set.filter(asaba=True).values('polymorphic_ctype_id','quote').annotate(total=Count('id'))
        if calc.correction==True and calc.shares_corrected != 0:
            if calc.excess == True:
                multiplier = calc.shares_corrected // calc.shares_excess
                share = self.share
            elif calc.shortage == True:
                multiplier = calc.shares_corrected // calc.shares_shorted
                share = self.shorted_share
            else:
                multiplier = calc.shares_corrected // calc.shares
                share = self.share
            if correction_set.count() == 1:
                if self.shared_quote == True:
                    self.corrected_share = share
                else:
                    self.corrected_share = share * multiplier
            elif self.asaba == True and asaba_set.count() == 2 :
                males = calc.heir_set.filter(asaba=True, sex='M').count()
                females = calc.heir_set.filter(asaba=True, sex='F').count()
                asaba_count = calc.heir_set.filter(asaba=True).count()

                if self.sex == "M":
                    self.corrected_share = share * multiplier // (2 * males + females) * 2
                else:
                    self.corrected_share = share * multiplier // (2 * males + females)
            else :
                count = calc.heir_set.filter(polymorphic_ctype_id=self.polymorphic_ctype_id).count()
                if self.shared_quote == True:
                    self.corrected_share = share * multiplier // count
                else:
                    self.corrected_share = share * multiplier

            self.save()
            return self.corrected_share

    def set_amount(self, calc):
        estate = calc.deceased_set.first().estate
        amount = 0
        if calc.correction == False:
            if calc.excess == True:
                amount = estate / calc.shares_excess * self.share
            elif calc.shortage == True:
                amount = estate / calc.shares_shorted * self.shorted_share
            else:
                amount = estate / calc.shares * self.share
        else:
            amount = estate / calc.shares_corrected * self.corrected_share
        self.amount = amount
        self.save()
    def get_fraction(self):
        return Fraction(self.quote).limit_denominator()
    def clear(self):
        self.quote = 0
        self.shared_quote = False
        self.share = 0
        self.corrected_share = 0
        self.amount = 0
        self.asaba = False
        self.blocked = False
        self.quote_reason = ""
        self.correction = False
        self.shorted_share = 0
        self.save()

class Father(Heir):
    """Father class"""
    def add(self, calc, father):
        calc.deceased_set.first().add_father(father=father)
    def get_quote(self, calc):
        if calc.has_male_descendent():
            self.quote = 1/6
            self.quote_reason = _("father gets 1/6 prescribed share because of male decendent")
        elif calc.has_female_descendent():
            self.quote = 1/6
            #self.asaba = True
            self.quote_reason = _("father gets 1/6 plus remainder because of female decendent")
        else:
            self.asaba = True
            self.quote_reason = _("father gets the remainder because there is no decendent")
        self.save()
        return self.quote


class Mother(Heir):
    """Mother class"""
    def add(self, calc, mother):
        calc.deceased_set.first().add_mother(mother=mother)

    def get_quote(self, calc):
        if calc.has_descendent() or calc.has_siblings():
            self.quote = 1/6
            self.quote_reason = _("mother gets 1/6 becasue of decendent or siblings")
        elif calc.has_spouse() and calc.has_father():
            if calc.deceased_set.first().sex == 'M':
                self.quote = 1/4
                self.quote_reason = _("mother gets 1/3 of the remainder which is 1/4.")
            else:
                self.quote = 1/6
                self.quote_reason = _("mother gets 1/3 of the remainder which is 1/6")
        self.save()
        return self.quote



class Husband(Heir):
    """Husbnad class"""
    def add(self, calc, husband):
        calc.deceased_set.first().add_husband(husband=husband)

    def get_quote(self, calc):
        if calc.has_descendent():
            self.quote = 1/4
            self.quote_reason = _("husband gets 1/4 becuase of decendent")
        else:
            self.quote = 1/2
            self.quote_reason = _("husband gets 1/2 becuase there is no decendent")
        self.save()
        return self.quote

class Wife(Heir):
    """Wife class"""
    def add(self, calc, wife):
        calc.deceased_set.first().add_wife(wife=wife)

    def get_quote(self, calc):
        if calc.heir_set.instance_of(Wife).count() == 1:
            if calc.has_descendent():
                self.quote = 1/8
                self.quote_reason = _("wife gets 1/8 becuase of decendent")
            else:
                self.quote = 1/4
                self.quote_reason = _("wife gets 1/4 becuase there is no decendent")
        else:
            if calc.has_descendent():
                self.quote = 1/8
                self.quote_reason = _("wives share the qoute of 1/8 becuase of decendent")
            else:
                self.quote = 1/4
                self.quote_reason = _("wives share the quote of 1/4 becuase there is no decendent")
            self.shared_quote = True
        self.save()
        return self.quote

class Daughter(Heir):
    """Daughter Class"""
    def add(self, calc, daughter, mother, father):
        calc.deceased_set.first().add_daughter(daughter=daughter, mother=mother, father=father)

    def get_quote(self, calc):
        if calc.has_son():
            self.asaba = True
            if calc.heir_set.instance_of(Daughter).count() > 1:
                self.shared_quote = True
        elif calc.heir_set.instance_of(Daughter).count() == 1:
            self.quote = 1/2
            self.quote_reason = _("Daughter gets 1/2 when she has no other sibling/s")
        else:
            self.quote = 2/3
            self.shared_quote = True
            self.quote_reason = _("Daughters share the quote of 2/3 when there is no son/s")
        self.save()
        return self.quote

class Son(Heir):
    """Son Class"""
    def add(self, calc, son, mother, father):
        calc.deceased_set.first().add_son(son=son, mother=mother, father=father)

    def get_quote(self, calc):
        if calc.heir_set.instance_of(Son).count() > 1:
            self.shared_quote = True
        self.asaba =  True
        self.quote_reason = _("Son/s share the remainder or all amount if no other heir exist")
        self.save()
        return self.quote

class Brother(Heir):
    pass

class Sister(Heir):
    pass

class GrandFather(Heir):
    pass

class GrandMother(Heir):
    pass

class SonOfSon(Heir):
    pass

class DaughterOfSon(Heir):
    pass

class PaternalHalfSister(Heir):
    pass

class PaternalHalfBrother(Heir):
    pass

class MaternalHalfSister(Heir):
    pass

class MaternalHalfBrother(Heir):
    pass
