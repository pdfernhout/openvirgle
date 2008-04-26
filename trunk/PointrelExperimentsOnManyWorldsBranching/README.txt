Copyright 2006[2007 Paul D. Fernhout
These three subfolders are released under the GPL version 3 or later.
  http://www.gnu.org/licenses/gpl.html
  
Variations on theme of Pointrel triples (RDF-like) from a many worlds branching perspective.

From:

Date: Sat, 26 Apr 2008 03:24:00 -0400
From: "Paul D. Fernhout" <p...@kurtz-fernhout.com>
MIME-Version: 1.0
To:  openvirgle@googlegroups.com
Subject: Moving forward & refactoring worries (was Re: Buggy software)

...

disclosure re Pointrel: :-)
(*) And of course, along the lines Bryan raises on branching, I have an
unreleased version of Pointrel :-) based on many worlds type branching, but
it is potentially slower. Essentially every triple (really a quad with a
prior field) links to a prior triple in a potentially infinite branching
pattern with reified crosslinks (triples referencing other triples which may
or may not be in the same branch), and search is done from one or more
triples on back down the tree (so indexing for speed is hard, though not in
theory completely impossible). The neat thing about that is that to
represent a branch at any point in time, you just need to hold onto one
triad, since you recurse down from it to tell you all the previously added
triads in that branch (and perhaps down into a shared trunk.) [Clojure does
something a bit related by defining an iterator so that a cons cell
satisfies the definition.] Combine that with having search and add paths
with multiple starting triads, and you have a very general system. You have
to be very careful to hold onto the latest triple in a branch you care about
though, otherwise. depending on how it is implemented, that line of history
can disappear. :-) So a reference to a triple might even get stored in a
file, although, you can also associate them with symbols inside the system.
"Now" is essentially a triple. :-) And since you can represent bytes as 256
reserved triples, and have a reserved triple for a symbol table etc., this
one recursive triple type can be used to represent anything. That approach
isn't optimal for, say, storing video, of course, Think of this triple (plus
prior link) as a step up from a Lisp Cons Cell of just two elements.
Actually I coined the term Pointrel (which by coincidence means something
related to engraving) while sitting in a student lecture given at the PU
PICCC (dorm computer room) around 1982 by Lee Iverson on Lisp.
  http://www.ece.ubc.ca/~leei/
And while listening to him talk (a great guy, and this means no offense to
his presentation, I often get ideas while listening to people talk, and his
was a great talk), I thought (knowing C) that what really interested me was
pointers and relationships, not lists. :-)  Then I ran off and asked around
until I got a blank notebook as a gift (offered to pay) from a friend of a
friend (DC, friend of GD, who left PU for another school later, no surprise
being so generous and thus out of step with PU) since the stores were
closed. :-)  And the rest, as they say, is non-history. :-) I had done stuff
with triples before, but not under that name or with quite that sense of
coherence I got from the Lisp comparison. And I write this all here as prior
art in case someone tries to patent it later. :-) Now you know all the
Pointrel secrets worth knowing. :-) Maybe. :-) And probably some hardcore CS
type out there will burst my bubble by giving me a standard name for this --
which is OK and appreciated. :-) And probably someday that all might have
special hardware triple accelerators. :-) Though you can potentially do some
faster lookup using a tag for each branch for quick testing and otherwise
indexing similar to the ones on sourceforge (though you need to track when
the tags change when you search on triples).