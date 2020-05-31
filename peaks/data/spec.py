'''
Implementation of data manager class and underlying spectrum
representation.
'''
import pandas as pd
from os.path import basename

__all__ = ["Spectrum"]


class Spectrum(object):
    '''
    Container for pandas dataframe representing the spectrum
    and other metadata.
    '''

    def __init__(self, df, id, specunit="", frequnit="",
                 name="", freqcol=0, speccol=None):
        # Assign this spectrum an ID
        self.id = id

        # Assume that the passed df only has two columns
        # TODO refactor to allow multi-column support.
        speccol = 1 if freqcol == 0 else 0

        self.data = df.copy()
        self.specname = df.columns[speccol]
        self.freqname = df.columns[freqcol]

        self.specunit = specunit
        self.frequnit = frequnit

        self.name = name
        self.is_plotted = False

    @staticmethod
    def FromDataframe(df, id=-1, specunit="", frequnit="",
                      name="", freqcol=0, speccol=1):
        '''
        Initialize a new Spectrum object from a data frame.
        '''
        df_slice = df[[freqcol, speccol]]
        return Spectrum(df, id, specunit=specunit, frequnit=frequnit,
                        name=name, freqcol=0, speccol=1)

    @staticmethod
    def FromArrays(freq, spec, id=-1, specunit="", frequnit="",
                   name=""):
        df = pd.DataFrame({'frequency': freq, 'signal': spec})
        return Spectrum(df, id, specunit=specunit, frequnit=frequnit,
                        name=name, freqcol=0, speccol=1)

    def getx(self):
        return self.data[self.freqname]

    def gety(self):
        return self.data[self.specname]

    def __str__(self):
        return "{}: {}-{} {}".format(
            self.name,
            min(self.data[self.freqname]),
            max(self.data[self.freqname]),
            self.frequnit
        )
