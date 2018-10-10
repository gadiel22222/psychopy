#!/usr/bin/env python
# -*- coding: utf-8 -*-


# Part of the PsychoPy library
# Copyright (C) 2018 Jonathan Peirce
# Distributed under the terms of the GNU General Public License (GPL).

from collections import deque
import os
import psychopy
from psychopy.visual.basevisual import (BaseVisualStim,
                                        ContainerMixin,
                                        ColorMixin)
import pandas as pd


__author__ = 'Jon Peirce, David Bridges, Anthony Haffey'


class Form(BaseVisualStim, ContainerMixin, ColorMixin):
    """A class to add Forms to a `psycopy.visual.Window`

    The Form allows Psychopy to be used as a questionnaire tool, where
    participants can be presented with a series of questions requiring responses.
    Form items, defined as questions and response pairs, are presented
    simultaneously onscreen with a scrollable viewing window.

    Example
    -------
    survey = Form(win, items=[], size=(1.0, 0.7), pos=(0.0, 0.0))

    Parameters
    ----------
    win : psychopy.visual.Window
        The window object to present the form.
    items : List of dicts or csv file
        a list of dicts or csv file should have the following key, value pairs / column headers:
                 "qText": item question string,
                 "qWidth": question width between 0:1
                 "aType": type of rating e.g., 'choice', 'rating', 'slider'
                 "aWidth": question width between 0:1,
                 "aOptions": list of tick labels for options,
                 "aLayout": Response object layout e.g., 'horiz' or 'vert'
    textHeight : float
        Text height.
    size : tuple, list
        Size of form on screen.
    pos : tuple, list
        Position of form on screen.
    itemPadding : float
        Space or padding between form items.
    units : str
        units for stimuli, e.g., 'height', 'norm', 'pixels' etc.
    """

    def __init__(self,
                 win,
                 name='default',
                 items=None,
                 textHeight=.03,
                 size=(.5, .5),
                 pos=(0, 0),
                 itemPadding=0.05,
                 units='height',
                 ):

        super(Form, self).__init__(win, units)
        self.win = win
        self.name = name
        self.items = self.importItems(items)
        self.size = size
        self.pos = pos
        self.itemPadding = itemPadding
        self.units = units

        self.labelHeight = 0.02
        self.textHeight = textHeight
        self._items = {'question': [], 'response': []}
        self._baseYpositions = []
        self.leftEdge = None
        self.rightEdge = None
        self.topEdge = None
        self.virtualHeight = 0  # Virtual height determines pos from boundary box
        self._scrollOffset = 0
        # Create layout of form
        self._doLayout()

    def importItems(self, items):
        """Import items from csv or excel sheet and convert to list of dicts.
        Will also accept a list of dicts.

        Note, for csv and excel files, 'aOptions' must contain comma separated values,
        e.g., one, two, three. No parenthesis, or quotation marks required.

        Returns
        -------
        List of dicts
            A list of dicts, where each list entry is a dict containing all fields for a single Form item
        """

        def _checkOptions(options):
            """A nested function for testing the number of options given

            Raises ValueError if n Options not > 1
            """
            if not len(options) > 1:
                raise ValueError("You need to provide at least two possible options for your item responses.")

        def _checkHeaders(fields):
            """A nested function for testing the names of fields in any given set of items

            Raises NameError if fields do not match required survey fields
            """
            surveyFields = ['aWidth', 'aLayout', 'qText', 'aType', 'qWidth', 'aOptions']
            if not set(surveyFields) == set(fields):
                raise NameError("You need to use the following fields/column names for your items...\n{}"
                                .format(surveyFields))

        # Check for list of dicts that may be passed through Coder
        if isinstance(items, list):  # a list of dicts
            for dicts in items:
                _checkHeaders(dicts.keys())
                _checkOptions(dicts['aOptions'])
            return items
        elif isinstance(items, dict):  # a single entry
            _checkHeaders(items.keys())
            _checkOptions(items['aOptions'])
            return [items]
        elif os.path.exists(items):
            if '.csv' in items:
                newItems = pd.read_csv(items).dropna()
            elif '.xlsx' in items or '.xls' in items:
                newItems = pd.read_excel(items).dropna()
            else:
                raise TypeError("Form only accepts csv or Excel (.xlsx, .xls) files.")
            psychopy.logging.warn("Dropped rows with NaN values from imported file")
            # Check column headers
            _checkHeaders(list(newItems.columns.values))
            # Convert options to list of strings
            newItems['aOptions'] = newItems['aOptions'].str.split(',')
            # Check that each answer option has more than 1 option
            [_checkOptions(options) for options in newItems['aOptions']]
            # Transpose to list of dicts
            newItems = newItems.T.to_dict().values()
            return newItems
        else:
            raise OSError("Filename does not exist: '{}'".format(items))

    def _setQuestion(self, item):
        """Creates TextStim object containing question

        Returns
        -------
        psychopy.visual.text.TextStim
            The textstim object with the question string
        qHeight
            The height of the question bounding box as type float
        qWidth
            The width of the question bounding box as type float
        """
        question = psychopy.visual.TextStim(self.win,
                                   text=item['qText'],
                                   units=self.units,
                                   height=self.textHeight,
                                   alignHoriz='left',
                                   wrapWidth=item['qWidth'] * self.size[0])

        qHeight = self.getQuestionHeight(question)
        qWidth = self.getQuestionWidth(question)
        self._items['question'].append(question)

        return question, qHeight, qWidth

    def _setResponse(self, item, question):
        """Creates slider object for responses

        Returns
        -------
        psychopy.visual.slider.Slider
            The Slider object for response
        aHeight
            The height of the response object as type float
        """
        pos = (self.rightEdge - item['aWidth'] * self.size[0], question.pos[1])
        aHeight = self.getRespHeight(item)

        # Set radio button choice layout
        if item['aLayout'] == 'horiz':
            aSize = (item['aWidth'] * self.size[0], 0.03)
        elif item['aLayout'] == 'vert':
            aSize = (0.03, aHeight)

        if item['aType'].lower() in ['rating', 'slider']:
            resp = psychopy.visual.Slider(self.win,
                                 pos=pos,
                                 size=(item['aWidth'] * self.size[0], 0.03),
                                 ticks=[0, 1],
                                 labels=item['aOptions'],
                                 units=self.units,
                                 labelHeight=self.labelHeight,
                                 flip=True)
        elif item['aType'].lower() in ['choice']:
            resp = psychopy.visual.Slider(self.win,
                                 pos=pos,
                                 size=aSize,
                                 ticks=None,
                                 labels=item['aOptions'],
                                 units=self.units,
                                 labelHeight=self.textHeight,
                                 style='radio',
                                 flip=True)

        self._items['response'].append(resp)
        return resp, aHeight

    def getQuestionHeight(self, question=None):
        """Takes TextStim and calculates height of bounding box

        Returns
        -------
        float
            The height of the question bounding box
        """
        return question.boundingBox[1] / float(self.win.size[1] / 2)

    def getQuestionWidth(self, question=None):
        """Takes TextStim and calculates width of bounding box

        Returns
        -------
        float
            The width of the question bounding box
        """
        return question.boundingBox[0] / float(self.win.size[0] / 2)

    def getRespHeight(self, item):
        """Takes list and calculates height of answer

        Returns
        -------
        float
            The height of the response object
        """
        if item['aLayout'] == 'vert':
            aHeight = len(item['aOptions']) * self.textHeight
        elif item['aLayout'] == 'horiz':
            aHeight = self.textHeight

        # TODO: Return size based on response types e.g., textbox
        return aHeight

    def _setScrollBar(self):
        """Creates Slider object for scrollbar

        Returns
        -------
        psychopy.visual.slider.Slider
            The Slider object for scroll bar
        """
        return psychopy.visual.Slider(win=self.win, size=(0.03, self.size[1]),
                             ticks=[0, 1], style='slider',
                             pos=(self.rightEdge, self.pos[1]))

    def _setBorder(self):
        """Creates border using Rect
        Returns
        -------
        psychopy.visual.Rect
            The border for the survey
        """
        return psychopy.visual.Rect(win=self.win, units=self.units, pos=self.pos,
                           width=self.size[0], height=self.size[1])

    def _setAperture(self):
        """Blocks text beyond border using Aperture

        Returns
        -------
        psychopy.visual.Aperture
            The aperture setting viewable area for forms
        """
        return psychopy.visual.Aperture(win=self.win, name='aperture',
                               units=self.units, shape='square',
                               size=self.size, pos=(0, 0))
    def _getScrollOffet(self):
        """Calculate offset position of items in relation to markerPos

        Returns
        -------
        float
            Offset position of items proportionate to scroll bar
        """
        sizeOffset = (1 - self.scrollbar.markerPos) * (self.size[1]-self.itemPadding)
        maxItemPos = min(self._baseYpositions)
        return (maxItemPos - (self.scrollbar.markerPos * maxItemPos) + sizeOffset)

    def _doLayout(self):
        """Define layout of form"""
        # Define boundaries of form
        self.leftEdge = self.pos[0] - self.size[0]/2.0
        self.rightEdge = self.pos[0] + self.size[0]/2.0
        self.topEdge = self.pos[1] + self.size[1]/2.0

        # For each question, create textstim and rating scale
        for item in self.items:
            # set up the question text
            question, qHeight, qWidth = self._setQuestion(item)
            # Position text relative to boundaries defined according to position and size
            question.pos = (self.leftEdge,
                            self.topEdge
                            + self.virtualHeight
                            - qHeight/2 - self.itemPadding)
            response, aHeight, = self._setResponse(item, question)
            # Calculate position of question based on larger qHeight vs aHeight.
            self._baseYpositions.append(self.virtualHeight
                                        - max(aHeight, qHeight)  # Positionining based on larger of the two
                                        + (aHeight/2)            # necessary to offset size-based positioning
                                        - self.textHeight)       # Padding for unaccounted marker size in slider height
            # update height ready for next row
            self.virtualHeight -= max(aHeight, qHeight) + self.itemPadding

        # position a slider on right-hand edge
        self.scrollbar = self._setScrollBar()
        self.scrollbar.markerPos = 1  # Set scrollbar to start position
        self.border = self._setBorder()
        self.aperture = self._setAperture()

    def _inRange(self, item):
        """Check whether item position falls within border area

        Parameters
        ----------
        item : TextStim, Slider object
            TextStim or Slider item from survey

        Returns
        -------
        bool
            Returns True if item position falls within border area
        """
        upperRange = self.size[1]/2
        lowerRange = -self.size[1]/2
        return (item.pos[1] < upperRange and item.pos[1] > lowerRange)

    def draw(self):
        """Draw items on form within border area"""
        decorations = [self.border]  # add scrollbar if it's needed
        fractionVisible = self.size[1]/(-self.virtualHeight)
        if fractionVisible < 1.0:
            decorations.append(self.scrollbar)

        # draw the box and scrollbar
        for decoration in decorations:
            decoration.draw()
        self.aperture.enable()

        # draw the items
        for element in self._items.keys():
            for idx, items in enumerate(self._items[element]):
                items.pos = (items.pos[0], self.size[1]/2 + self._baseYpositions[idx] - self._getScrollOffet())
                # Only draw if within border range for efficiency
                if self._inRange(items):
                    items.draw()

    def getData(self):
        """Extracts form questions, response ratings and response times from Form items

        Returns
        -------
        dict
            A dictionary storing lists of questions, response ratings and response times
        """
        formData = {'questions': deque([]), 'ratings': deque([]), 'rt': deque([])}
        [formData['questions'].append(element.text) for element in self._items['question']]
        [formData['ratings'].append(element.getRating()) for element in self._items['response']]
        [formData['rt'].append(element.getRT()) for element in self._items['response']]
        return formData

    def formComplete(self):
        """Checks all Form items for a response

        Returns
        -------
        bool
            True if all items contain a response, False otherwise.
        """
        return None not in self.getData()['ratings']


if __name__ == "__main__":

    # create some questions
    questions = []
    genderItem = {"qText": "What is your gender?",
                 "qWidth": 0.7,
                 "aType": "choice",
                 "aWidth": 0.3,
                 "aOptions": ["Male", "Female", "Other"],
                 "aLayout": 'vert'}
    questions.append(genderItem)
    # then a set of ratings
    items = ["running", "cake", "eating sticks", "programming",
             "tickling", "being tickled", "cycling", "driving", "swimming"]
    for item in items:
        entry = {"qText": "How much do you like {}".format(item),
                 "qWidth": 0.7,
                 "aType": "rating",
                 "aWidth": 0.3,
                 "aOptions": ["Lots", "Not a lot"],
                 "aLayout": 'horiz'}
        questions.append(entry)

    # create window and display
    win = psychopy.visual.Window(units='height', allowStencil=True)
    title = psychopy.visual.TextStim(win, "My test survey", units='height', pos=[0,0.45])
    survey = Form(win, name="survey", items=questions, size=(1, 0.7), pos=(0.0, 0.0))

    for n in range(600):
        survey.draw()
        win.flip()