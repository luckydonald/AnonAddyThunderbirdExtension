[pyte](https://pyte.readthedocs.io/en/latest/index.html)

There are two important classes in `pyte`: [`Screen`](https://pyte.readthedocs.io/en/latest/api.html#pyte.screens.Screen "pyte.screens.Screen") and `Stream`. The Screen is the terminal screen emulator. It maintains an in-memory buffer of text and text-attributes to display. The Stream is the stream processor. It processes the input and dispatches events. Events are things like `LINEFEED`, `DRAW "a"`, or `CURSOR_POSITION 10 10`. See the [API reference](https://pyte.readthedocs.io/en/latest/api.html#api) for more details.

In general, if you just want to know what’s being displayed on screen you can do something like the following:

\>>> from \_\_future\_\_ import unicode\_literals
\>>> import pyte
\>>> screen \= pyte.Screen(80, 24)
\>>> stream \= pyte.Stream(screen)
\>>> stream.feed(b"Hello World!")
\>>> screen.display
    \['Hello World!                                                                    ',
     '                                                                                ',
     '                                                                                ',
     '                                                                                ',
     '                                                                                ',
     '                                                                                ',
     '                                                                                ',
     '                                                                                ',
     '                                                                                ',
     '                                                                                ',
     '                                                                                ',
     '                                                                                ',
     '                                                                                ',
     '                                                                                ',
     '                                                                                ',
     '                                                                                ',
     '                                                                                ',
     '                                                                                ',
     '                                                                                ',
     '                                                                                ',
     '                                                                                ',
     '                                                                                ',
     '                                                                                ',
     '                                                                                '\]

**Note**: `Screen` has no idea what is the source of bytes fed into `Stream`, so, obviously, it **can’t read** or **change** environment variables, which implies that:

*   it doesn’t adjust LINES and COLUMNS on `"resize"` event;
*   it doesn’t use locale settings (LC\_\* and LANG);
*   it doesn’t use TERM value and expects it to be “linux” and only “linux”.

And that’s it for Hello World! Head over to the [examples](https://github.com/selectel/pyte/tree/master/examples) for more.
