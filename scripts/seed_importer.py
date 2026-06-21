"""追加知识库数据到 ChromaDB（只增加不删除）
放在 /scripts/ 目录下，需要安装：
  uv add chromadb scikit-learn jieba
执行：
  python scripts/seed_importer.py
"""
import os, sys, json, base64, gzip, hashlib, re, pickle
import chromadb

# ---- 下面是压缩嵌入的 121 条种子数据 ---- #
DATA = """H4sIAPMAOGoC/+19aVcbV7bo9/cratlr3QbHoFlCWTf3Ptomab/21Ma5ffs1vcoaSkYdEFwkkvh1+i6wDQjMZBtszGCMbQxxwuB4YjQf3vf3I9KqkvSp/8Lb++xzSqekkpCtpDuddlZ3IqrOuM8+e967fv8/FOVP8H9FOZLs6u2JaEc+VI4Y918Z968bd4aMpUdHjtPbSFcipSVS+Pqokh8Yy+7fzG1e03eeZLZm9ZGl/NCEcW8nd20///C68fJG9vludndR+b5vSjFG+oz5Dbsh49HiyVSn2uQLuJ2BJs8RaPPn4++yuqOKq1HJL21n59aNJ1dzK+m2xLFjVa742DFjZiOz1ZfZeppfeKhP3sxOvdRH5uTe+vyOcW8jO3tdaT6l5N4M6CNf64PPs2t39O3n+sTmX/dGc/fH9Mm0/nglt7GWW+0zVpf0+zf+upc+ffrMX/eG/9LXb9x9pe9M0Lzwp/541tiZNKY3jbF16osP1+9Ds+z8DWPhQH82nX28k10bJljCFJmtHb6avr3sxFpmZ0e/OWNMTGbezP11b7Yt0aCYm5QHgkXk1pf09C1HfuE+/dJfL2f256Ed7B6ewAItvWUQ0RaUDxRav9gX60DtjPFbsBoChzG1YYz247v8o/H8va9hjNwawH7cgM2NHBjXF7OLy/haf/y1sTkFL8xJAbj6wPNc/5SeHjTuT7YljrJDdSnGgy394BohgD73pi1x6dKltsT3U6PfT/X94/xvEpd8VbH5Jzu1aqRfZ6dHAfmUuo97GFZH6+2awgh8mJ/w9ieLFgr/+tXFM6d9CqEjf3SiPdSTavxjUoEjzS2t8qdwu/SN7dzGAsCCteXPLQNOHbaCb3+EXVUz5oxYaAVi51JDXncgGgv535nYVQEB+X97PwI03mrMmbKob0Xrt8HoOz/Crt5uTLsL/XEomWo+Dzg8OZ79ZkOp+2Uo8lm5u/xD3ObJH5EQTCql9/hCS+tFBTeYe72RnXombif712+1cGsXbDeltKZ6tFCnYowv6xOPlMIdLh7NEeqOO45Z4CHeJNkQak9vQqlrbW0xXvbrexP15caaeqdrO1MVLXk3ijKjVEEK3Gok4gkFo073j0wK9v5+d//tSEH1hOCHvf81jWZHCICPNV+GM1L0vWnj9rj+7KpSdzqUuAxcL56o//kwdthP6ly3loD91n1y+kyDt+HjjlCyvV75fnDy+8FbirlnDg57hg7/ar2STGmdyvmers7ulFKX23iS3R0k2TC3cl1P3wMJ1OMHCR1EV33gdX0R1fj7ywd9byMfvA0H3/sJnPxMRTrmUd2xYCgSi/hqoGNvJwHc2fspivSEm3jZHQppduziX+zq6kgq/wJ8sasndFmrf7e7/+3f8FUZSUO6sXx7O7fZX7n1Tf1gkG8GBfhnS/rajH51Ff8koAztQxfW+1xPKNKhKRdOthZYfmHg813J1OUeLQk/z2idXT1X2NNWjwmrOlJEHbxzXXZqMbOzQuuptxuxLrM3CxoFvWsNfa71iIHuDGV2X9Fzbg9YG643JYxSwaQaCvPib/iqjEzzlgSm76dBYJhW39DQUIHQeNWw5tdcQa9Wi6HI3SjMUw/SbYmvFLij2Z0V5Sv+FH5kh9PG/Lf4Y2o13zelfAXNGtg/9v/BUY4d04fHQOg/dgz6kb77gXKiFRD3K6UB/q/fHtN3pkCKJS04v/QS1X3W9auCMvyV4m38ki1lJrtzAKqxw1h8lh15hb/yy3v4n8zuU9CXs3MzonNnqOezaNcXiYZ4CqZsj19u74D/8+Fw6uZT+tz97NpUdvb6Gd7W2PrOWLyN5pfdR9kH/flvZjI762LAj7VUpJ2J+Q7lghaKhsIdGpfpaUBTIs9tvDaAwgkAMK2HAeD8lVR7VwJ+fD+87Gl0ueFXZms3u3cnu3qDDGTmZFxlYk2djS6XD36aeoaxNAgHKtp++nk80tWTEG09OGxz6yfQbH4MBAX93qpoWZA7RFtsykQQ65DY8JOeUHe7aOg2GwLYjb7+7PpSdhIkkXFO4/hem0+xfcryjz6wp69vo4EMVRV+6hvboAYpkmikkAUNx6mA6T7VH3IHY2F/4J0xHXcH4lR3O2hkbG+uRlcjAlc2RKJt8NUNfeTgA33tUW7kqtG38te9YQGc//zkl11Ajqm7u9EJP/Jzg0Z6Ul97ktl+QEOIxuevXOzqibTLjU+3XjxTPJ0+sZHvGzYnOXbM5CSEOET+W39zWqnrTl6JdHVfrhdohEMSLTdG+zPbA/roHfNciN2ItXAWUxf5UqWf+UfjxoM9cSrEMki6pOmNxeXchnkdifEQq+A9FteM+UUyTdGEsBW3M7e/buze1EdWs0/vgq5bsivaUigRDSXhLp3t7Tx/hQ/Id/34OiEX2TzF/LD75o5Iu9Z5RYbmuQtnFLSkCngZt8cy+/Pm5WMAYBMCzSFclDmxmJfxvMzWSGbvgcMYWdZvjugbe/rQjjkOY9dsnN7PeSd+mzNvFnIv79CFwOaVibVfDfiC4agn4KuFWHsalezcur4/nd29DU05m3B80dXzWbI7FNEc3T1df9QiqaQDmd488RMFxojFLzuEfGZyQyWEN1vt6OhUqQkQSdgY++eognZuup3M9L8OR9zZFdU6HKCZdGs9oVRvj+ZIdjtSKM8xE3hhxmhXJGkzX/OFE786dbHlxMVPL7Q0dkZloeIoUK1vaevyQKFkUoPdlNOQjyr5hXtAlnIvrxs7k4gOL4GgThNSyOPEuB1ZWpR4FU9EtS8b21OdHTbDfz8/wEi1xKXw1o5Nw29gYMAR+c6tY0aS8vat75KpKx1aI7QongvmMR68BnIJMxivn+VuL2RXbiIXvr4Ir/IPZyxTWSGLGNDRFYo2wBGFOszRj4LGvQ23kcYtXecfyy8z1N2NPLMsSGj3+b7d3JubuOBXaaN/Q5+4me/rdwDawKEAa3EA18ptXhNgqnA/Aqo/3BT2+gJNtWhNtvuI2++DWSY3+3OPBmD5ZGG70JtwILOVlmwP7ghKKMmScQk4ZMI3IePNPtulR3p6QV+5QXTamHth3Nm0TDF1OM7DeTKxCiEvIb6M6cmeiA2SdwLzb+y+Yj8mLloIHniyA8uMeqfJrOmgmYhUOk6cu9Bqi/KMlpSik4XUlK6AJi+2i6Bra3cHViDZOIznq/rgqO3UjAI5lPKb4yMAMVu4i7i6MQHDCtqPjk59ZDF3bV9fXLQ5czFLd0cooYp7VtjJUaWMEzFtPOrLHKwDW5nO9/U5jDvbcAWBcjj0m6vcA5k5WMi8mctOvawwbaIrodpMjZTvftmZpwfys/OO7N5O/t5rR35oLHcwlNvfP+wONqlBrz/sCkViP/AdFEtXk6lQKp5MxSNJ3MVRpWjp2fW7xvNpuB1Eb0EwAemqHGCioVRIjfUm410WzIZBS3zJiMvMVewgR6sjt/5GfzzkIJ9xpTPv0aLxSKpoCs4cSYgjCbfcAKl4p6YmtZ64llStgx21uJBNgZDLqA4UFh1c4qywwKgWiRdDgIAgOaBhWNopMXIHuagzezNAirjUQ6CuMFESBLBob0c8cbkIErLXGyaCf2d3rztyK7dyw985sjtPjIVFhz7wrb79nKTp8mwxFIupJQAHtkhLn+8D3coEkzGdhlkRw4FUOfSH96EJkIzc+nqFKXriyc/UUIfWkyrag+ydR/b+eDa7+wLQJbdxPbO36ciuDYNKzCF12CUKqrFA2OfWnJEf+BIl46neEEJGDX0R6tESWpJfIjmYAE9gdw9Qnh7yNTtE6ENZ0HyhhVLtWo/aGUoApe4R8DkqIhMOloC7k6yLAEoPAlNzkJLkkOMUKokofApkyEX3FaeQ+HEphU+SrbCssNLJVJSS19YFUCM1iYqMiV2MPVgVGVnf+UCoYEnF1LIqXUegSeFQUjtkJdFwCSc8qpiaTO7gPmjJBOxywEx6iqZQil6rHGTmREcVWf8pBrTo2JuKdxSYuHXQWLxDc+C/rIs/yrUoUsBk+6ZFLIn0xLvLS/LARa/PGsM34Gbgj/lvK0cNOFV/0O32+rzOGi6ZSeSvcK2pMdVVXglg2p7+aNOYGQcc6f2cY4EATuPleCp+OdHVo5XZ3yfxlKIf7Genl8mDU5WJz+VS/S5fyBkJuGtRG72N1rCh9KD+7Gpu40lu5REFFnkbXVyyZCZ6M+oGw8bIDpjvG2aRTrOgC2d3Nnhjix6Ubj3fDFD5696ocfcBNSDrEsHuL31XhcINSnSufzT34hGq4GxhhDBlTYumXfFSQVu7xOwGLzL7t0kv07eu6c/6YIX5pVf5a6vtWiiq9WAU2esnzafkMBp4ltla42Flozsg9WGrieeZrRvEAhw6hrTdJ3WfzWrqbGxSe91s1LRp6mNL2eEhsZ7R3NBTfX02sz1s7M7qI6vGwhKCaGtSn5jJXRs17m1IE5XqcTijPnld1uNsQtiEYEN8mP8HTti4NuCQGSizyZizkY53icyRVoVuVsCM6BBG7Amlzhhf0dOv4AmBkNOt9GvQZxSEFSDOGWBOQHzq6i8dVy7hfi5ooY6LIAudBAJJT3u7gVjC38n2cFeoJ/rbeKq98DLZ3vXFeRB6f8vBcQahAa8OsRO63KBFhjy+QLSpBkPhJVO7Y7BnqptgfbOmDucgDc6Rn+ozNvqVgpanMCyNp5o7OpghOynvV2yosFVsCtvr7dB+CbIscnXWq/BSdEHwgfylidfmGcb5SmWFdrbIKA2nxRRbbqFWLp2MJ7tDqUg7dGo0lV+aVH7Vwx7iVMeO+YFTr/BrQxjOLg+jCW0JVyMzlz3JbI0AicCoV32gP7e+ZYr4JtZmdnf1kSWS+IHBAqIa38LzQZBOGVF1myOt8ZF4bCdDaoHHdiIt6FjGUtpBwqEkkHjMEW+ItbHrguLkCMpMxtbXqB3k740Zmy8cIA7qI3MO434/0jjWEhQGZgKDwbxsMCQXYqOlmlh5HUwKMfWZA5n73B0x7i6bQq4ZDEpPyDQNEKOdk+zLRvKbI4n9yRKt8i98YCJrMDC95WItPc3s3MgvbRtbA0DT2ZgwIGE+4DUL3fUq2ZUxRt/ZeVe6hh7VHQhHw9EaovoakOjlZ14Z6y8JDCZsTWcQrKn8BbnEg3JhFNL7uX372oA++NL0IokhbC6gGECmnhzNyPUk+p6Pa2U7ZKdmssPbFj+V6PZJqPey3FEYyeHWcggz+aCUeAqpQ4mhY6ruFyxuzNSwo4Kg/qLQsBypRWmVu9+/H5xUiKAZz4aMvl264EUjWIiX1FnqTTgjBD+lPP3C7o3tgA0dV9SolgqB2FlYcDmayDp1Wl7UcziRFOMWsYaMFjJRhuxaTJIRhi2UYS6hnYxbxeAA0sKZpk9uAI8GBo1Xf+KR4nM6nex8vhJRfijEbBvPpyWHKJC6eX1nGhRuEO8O41Fe1RsJa36vx/XuPKqC+7UgKjmQKXzSchHXR1ZDRrtRXll6KUkBZRCo0Jvz+b5dwlA0l/Z2doZ6rqCDlR0h/LAeC8kZpkqT/XrHoe9d1be2FIyD6uyKfCZPbrFvcXQoTF9EW0mqgUX46GJ/UMRA3mLeRFei8tSllN2cvQx9B/UguztY/TIKoZ046/lzrReZi5obQoGLK8TGSRiTT61MF31y1FhbLm2O+0XVV+V6uNQ3c7CAWiGxRMZPizvS/VfJRkO+Iqk/XX2ZH4v+le6BD8S1iMelhby1yGpseZe1lMoNVJqEN+Ov9Yk7smQgbwv0g45Uu3RF+pf1ndfGoz5jcVm0Q5LxPD+1Dtwf0IAsfZw4NwDHPQPnKN/8Y8fgpTEM6tIweVALCDB7neJ/89f24W1m6zEQJ+oK3Br/d/NBAV0IVYy7r3IHU/rcfYYvf92b+/7mkmwkwFf6wGp+7hW0zGwvSo1peWiqB8F+LX/3BehcbHEkkuVer4Lclls/yN9dp6ayid8YvQp4zJojCSGql4UjHl+m7BoiJqR0CcLrkRDQGt1pS3i5s0A4BS7hkWR3r5NqaAaeCFwqF2+CvdAQKwcewM2kH3L8AV1H5r386HJHZ4O3IYbBB8cVyZX5kbMxcFzpDH2ppro+0xLJj5qA8hOyUF4UbD77eCe3MYaoNfQ0e/0VhW7wgExotvNEcfl+/UulNFzT6srA9KGFa0gyQFuA36Ss8YbcZy47PVBeV9HJoXaGui8p+tpdfWALHrIhlf+JbxSQ+vPLmwU1utLN86uaX/O7nFqwhpsnx4NYIkcYFrSmgF7AYxYUQMTIGhqQ9jpBESavoblpEVRSFHJAUQ4gq1LcgWmok6IjZOMc3VzZkwQkNLt6oyBWdTMPflsiqsWUcG+8I6oyTKyLpL786GxXQqv/EPAaU+hyG7tIQiQvuFLHvem2vvN67Af6i6kllg0JxoaglvAD9vgVEzvwDegYfDoZErRxfA+qQwT4BpBkWjhD7ePkCDuuJFn0sNrNooePK0AYI591d8Xh8HqOo50dKTnGU4TYKkB56NHgBiTIR8flKRb6ACxPgC7t8gFbqU78D6gxXzgaiHnePYMRYC87cBjbBLgWaUTsMUCx1EXA3gAUiQfQezJiszcAP7p17C+AgK0njb0MNJb1tLH3TY0WGzl7FoQ+38zoEzdBq0KKCkyFL8nlFM0bzMGkFbtctJmROXLs8kAY9gq2b9Hq2EOP2IjpYqHnsHXi6vQn7Jc7hJg/QFBtrxSjS3G5jFwTNtoQFrRbjQ6bzlJ0A+xe5wjxlULimCIZ+WRj8OHxg6UxhDIKsBicS1anH3LvS8j82+No7o5HQh1qlFsvVGyK5gx8L3wPsa4eLQIagXje3tURj4auqPFErEs80/6rN97diZcbr0pvEp/DjJra2duRiquEwjQ6WSBZomvB5XgY9W1SI16XFmsKu2ugvsCyGdYQVCxes0vSkwI0Pu/q6O3UcC+hRKjjyv/RJFebCjJogsn7xW5NM35LilqjKcs6Ni3TfwGqpio1xfm1z0MdvUiDpAUAE4aj6QwlIkx+s3OCmhFZDI85NhS8nxwVEsjNuaAaT1xWRQucuKsbVhKHnSfb4zFJYDwudRTt1R6tuwtUc0RiyZN62NkG1UDA6Y2GtEBNZ0tXmvZocbyaCC8Wz0VyC/5+iR522LvtBpELdHTEGfOSGwisMAeOheI9qMmxI/sSgVF4x4GDhlrUKKTnoENHyUguuYWlYDqZfNL+7GMDzI32oJiOCGSjoIrLLd58oWGkb1IoKPKuGJR68Gr3aHi3S/qGr6ikwbIjl/LFDzlyt1MNOD0hr+b01XTkRQyG3+uiuA8GFSBykd4OdoHk17ijwquSqJGSDVvACDevF2hnKPrH3mTKvqOlCYKQHbONRZcfdinTpD3ZxbNcMsNA7XVqKRz12DGZ2fMrUho6YKFCJjVIaFrUchvMN4i5nbCrKPOwW+kUDa9Bw0hcS0SuWCHNqAoARgzFvCnSEg/DH5fq88T8AV/MXxs7kEQDgool2oHBAwPLkng9OgEy7aDjxOHyYjMLTAr9pHvOZEjAmXjHFdaAHT7NSUESJqeQghH46djGLcgLsmlhPSXzfWFBjAiazy1GKzkA4jDou9WAP+IL+ILOmqBPIh0pQ5yslQRUmCRNvAKSk9RCPZF2sZ/UlW4mwlgbJIl7RbWUFkFJ53I7EPFIPIpXEAUaCfFNiixGMG87QLorEg+JRtb7LixCRcKSfNURBbo6OmgFpqxl0gikmRIITILPnjWfP2WFCUWAiEtPjUh2gqbkwTo8oNrtUZ0hf8TpjwVrcY37hKIBio7sEfc1ugqBv2YLrhz93ng5kVtJ6/dW9fVZtNPsryOB8juTf2DyNlqUylhVWWgF/OvOXluCm58/VEqbkZm/iizAF9Wk5d3Zs00vxjUU4ufJYpWeBPH+3802Ra/1x89yL5b/vS1RRy/+DZX4ogy+Om6+St8h61R92SRnAYmyi4PTQPWH5y+wuhjiH8napZjh3gD6XP8sXH7Oiqzr8jmJIX3gcpvM6bDFHZI49m01Gd64k//Veu6sckFLdgNz0T40/SPCjl5HXhdjdMh4MFRvvrb6R5S6fN+kvjmBwnh6UN+6VmhoNb7DcEwVM91cBc8K47yhjo6uCKMFSp1sPK+XkbPS1fOq4XCgyROLvrsKY/rYP7RzLtVX4UEi4BzuNCrvL/I1ugslVsw7zkosiGa/p3I0+vxqrn8EKdXSYO7NbX1gmS46M4DL5Rn+pHRS6MOHStuRxsbGtiPKn22vfKEPbXbUDJJWPiq2SRX2SAbTEO+sfY60ue5PfEoA5e9hyj/82XKO6ELgZgjcW0r7MuX4siGhfdHAuhcgDWwUDiWlMluSSlOwTQLWKcwmqhjjoMD3Z3fvkQlY7srMkyAD9aRYH9L8KY4+3zfLyhwVNQZhS2rKElrmC02nCkuKJwpt10dR4Z67rz8ewx4Li/JWf0/L+kNxmh5sILc0Sra8Aii7u6VAlV+E4r84rnD8FIdf6Qr41JDL5fP5Yu8eK30If/OrQS0W8bi84Vr4m79RouGsNeG+H/hbaeKXUke0tp5ZY5dW9ckxFhzEHPCT32S20Y5Oll9j5oG+eb3UmGPnijx3Xj3TfOrsxZazzWdPtKjnTzefNXUHipJH4X94BU4ps7UGB63v9enPpuH3cUCP7/DU05MOtMS+SuPb199ld4HG31bE6BcvNJ9t/bjlgnruwsmWCzj2/rcUWS8P7HA73aWD798C4MErj+3ILb/59NT5My1nL6rnzrdcaL546hwtHePHKbKf2bm+w0iXiY2S0Wk0B/zC2MidRds5ftvS8uvTvxNgMdMDqoIJ/CoPlvMXzmG2lfpxSwuBxUw4YFmlJxwt/9niaP2No/W8dfwTzWcdLWdP2ox5Qv24+dPTF9XT5z4x9TWMLDlgdr/5p5mdx8BR6pz12PfNAGX0sQXzN656GpXemKOebPkYFwprOoeZ8IBkTAdEi/f+9DsPXel6BdSgOxSIhTzhGiR/WPm5/wC0O32u+aR6+tTZFg4YU3WF306HywpddylcT7SqrSd+1XLyUxjjEwkK3DUkoMCcknR73cW5n0pdwR1ST149srcyT17BPSMHO6NbUvSnuGDekSsy6AJEd50Iv+Zh1kWB1JdYxNEl8lScIX3nkqKPTWfe3MCwyK0nCI6NaWN+R0+/ohkoxpl8HGweoPwAMeXSiXP/u0X97bkLv2YgPXUSbt6pi79TQTFQf93yu0sKBi2Nb+gPr+kTM+iOZ/Z9ARSPJcYZGLmnFBLcHyzlepK5GgvuSSAgNaQUBEmPwxJcfWgIr7tJjfqiXrcWqClNP9DIk2X0/du4b0qWYY4p2n0AawMyr2Jm/3b2+S6iFbfLsAguxCb2GkkMi9+XaHcZ56rePw+0og7+DyiT2QIh4jEmDTtZ4rQgUnLD/ZvZ3Xmzlbu4FTBt2+ECvjItreN5ilrJRN5mNkFH6wADoVH9Ia2AmgM3LDOTld7brDj3+nn+7haAF00PTIli7VxyEElpy8zWGDWuyy6tgy5ZmL2qTvBL7ucr7WdsjGV3DjD2YH6zXBvS14jglmtjIWiluyIEdCuEluiLwpQoJkTJRkDCXRBw/9+jOtlyiO6h/3sXL6++M0VYChe3yIIodzZfVeqPYWzWnjbDfaDYTlOZdwRVVzDidYe06Dtf6fx8n/7wvvHiTWZnB5f/EejN8rocSh1aEReG+N+wPVejr74eeAA80fv2eD8F03Hggdz3++FlboK0dEZDxcoTfeImi2erIvvA41T9Xm/M6fXWlH3QZPooWfUvkf5AWNOEcijpoCxGHp9/xZ9QdYb83RdIsvr2yjkOCdHvzTJPg+J0fuh0ApScTfjfr5TWX536+KJ68XfnWz5y8Ttx92vetImauvwlTd3UFPMEWFNq0qC4vSVNPdhUbMatyGFQlP6GbxlLYXVq89MHyFXSp0BgaGkGsewjD3nV9YOB/NKuC/pntqb0iae5a/v4B/U11h5B96KObuqYG3qub97EtshtJzb0x7NmP314o7Sfq4p+A68yu3eK+jn5QlnNisKePfx45d3qkyC19lEyIPwAzZl2BC0p45ZOmJXNhZvweAUEguzuGkdj0LPR2Tzrh1+sycYE0GnWcJYOGvpSEw8fBYbX14dh+LYjmMs4nYb/UoTK7HVaBltYZXx3qe6YMxp1av5a8D0ogjdECtdR9tClWONILlUKJLlEOij+bEv8CZZ+hF62wRzsT6al419tR6SIprYjx/GlFNaETTCyiT3u6la76UGQPShEO+FTDHiidvFOras3hc/84lF7PPFZPHGZZozGk6heR9uOtCX+zN4nu+lNY2MjixX59S+LgqYQxSa/If3dGhk1LBaN8Qc4yu9hSxV8+tBcgWmOw2wlXom2I3+AFUkmniDcSFleZPyO/ZLDd2GJIKtWDjQ7VDIl7zkGHv9au1JFAKTHrWp+VzCoeWrxPdCyULf+hLRT9cy5ky2n1V82t7aon144LdalL+5kl/pACtAXUIJpT6W6kx86HF3dWqIxHL/M0KkxkqBw3FAo6fjc61CKNt56vhm19+aLv2LeHyov/mCbKpLAE5s6JIfb8T0eNRIJhD1+f012fBZYw8w/oA1mdm7lnvRnXzxgvOTqtj60S7kqKLQxFmjGpDD1esdeFC5GgSJ/prE0yPxbZXOVRPGNmTeAYDxameKDLTHLXMIq8ZdK45/tSlQxRcWQZM77SPspjNzKffflhpSiZz+whFFxOZ35bgrD/ZZcPCWjUf7MoWk2nOuWpPvIC0Y/a5nVyn5XCp36QE4Nl0FAcdw2gDjJjO1lJqDITj7CEi+wJGftyDhhuuXKDCZn9Xwg5/RwhJA8utKwF4DOlRtQSushD8EH1F1P3+WrrXQRvaoz4I9GYjVFMsiZRtKqL3ZFu8qsmrdlmUcfkFmLOLeeHjLGuNu/+RTZ36nATGmaoaUMG7M6m/HIhKgH3+T7Fo3R4fyt9TrMBHvDNL1L/9Ubj3zWzE6pLnWlW2MjYcLmyKq+9I0+MAAMLH93Xd9+JWY+lJ750KHvcUadtX2/wQX0bK8PYwi3xvPXVrP73wmJSy48hc+A2YWR9yfg1f4BbF3B7OR0Figg/O6OdzN5v/dzJRSNKv8K5PkzgJmaCHVq/8YeQwulI84Km13u0bqVhrjyr+Q0+TfOSWleSo2xzBiJ2hH9tgQF2CpSjo3S0MmYjtLQzXJqcLWmF5VC0dl74EnonOpo70qmPqSG0hKovJP9plNaMsV8MDx0mjUVMeksZLEtIdrUdYd6Qp3Jj9qOkF8TsBaQC0RFM8C07QhJYJVO2q/6fK4mp99bgXPJso7NSWf2HxgzG/K3NXIH6Kyg0zVZgRyQRIJVZuu2vv6KfQbjtvF8NbMzTha00uIn+q1RJC6vl3lIlvT9DMs3PaSvaJCIijm/8ictbo0WBXBROkB25aYOJEaKkvtL39WjPK+b0rx5dqhlVYw8k0WOQijHB/WJ7zgMmMGTfRakEBsAf+ZGrur9Q0BfiAfhE2aYIXqBed0ShwI6KAOD55UWRRBTVsQicI5xaKzPPQChgZbG6fn8U2NhueibKUSyMQeIbRfEK2oMELKr6SISULlKLgGKzU6lVwiKaISUzgHmReDwuiajVLFFPiKejSofk7Sjor1yRBDwwRw3aWr0mk8yi7DE8kWSanHgHk5BKMkeyLYYmKXIOiNlxY5yA5HF0sKyV20DrAk9RodJWkKA3/3agY4c/fE8wFWenNxIiBHCKGhiB5ntEJuErQ/BLGZqSwQabcPVSvZKeCH7PHBMyXgGfxbyfNeGi8DQlmhqNGNi5IIqNAUzycovq0lLpnILtDCqxpId3gaBty0RZJuSg9AZjuQ2BvX0N2xG+glKde7gJplZjPWX1AOxgG1T3hENA1fZWdhGIYhdLgJDaL17mwVGFzZEWFgK6GKpRCaZqlPVfAEsqBN7ZxrrconbZ4bVsxsl330JIUXe+Cj6uYe4TEm2OuoHIGCkxBpyZ0K08NUhhhpIFGDo+VVqjiH0jGxyyQyIKh/UrtYOxtmPzFUAj0t1h3z+YNAZfWfwHBUTEwoK8xyzOjH8o1t487qxOYF8YnQH8AStjk+uwnNX4Pvr1/7b7YN/8/xnAAzDVxbxyb7EpKDR8vEK/Hb7Ojszu8uZrRF6CncZx3A2uL2Nwc5O3nQTk+yC+IC1vcFHZehfMqTLhdLuxAgNi3VImxp9nY6k9GhYniwAzRtcTvg3Gio8jUGc2wsdzHY0v18a9gY1bZKGvWHuVr6PhFIbtwzGPfXBzfzcNt6hudf5uVXkp7MvpB9PWd2RTdgYY3Ur9CP/5p4+9pp+G9/d0zdnoDEbbZf65ufn4Tf++GYGTghfbX9n3H2GFQNg9r3p3MvXONrCw+zKRnbnIPd6g9wHsOQKqORWY1EtqsVcrppQSaJC4tNV7PTmVuEVkRdjfpEBym/Mp+FQjLvf6unNJvMPvCIzt1HetoKNQMyBPrMMwxHMxHCeBh+MgfTw8Sw+ZmNQE7lrduVGSddgg8tVTV998FvoC9Im8Bfcy/NNMYLLDf1hG6jVb79w02DUMPdiMQcH+s1MYWOCplY4Do/qDTg1v8un1X6zCwrNILvZsmxjLE6iXmUaHe6iUEkyJnUzHmxjYBSczu4+04lAut4C8YbLZqygQuEbZhjFNj+cfdqP58zewXCgkXMRdHEZhFj0V8CURHQmx3MHcyDxGsMgVK0CDzemtlkZBZLqDwmMFYFGzA0sr6t4iNKgW2vX9fv5ewPUtcKheNWYFvQGg+FQLYdSji0XPiL3rry5QcnuPMcTmhzP7q7RAetDD0i3KeW8hAcyqKqKMhYaFktrkzdTAXI+1e3z+UJR1w+AzvZSB9uGlMmOdaRNWU58Tc+sYAC7Bb5P0M7s386tr2V3BQcT+kCBGyONZfoJpUWhjCttW75OklRTgOrhMdkcpHz90lLlYUQ+Q0kKBeVZmYn9HLHZtdK3nljECkADttoKR+VXg0F/1OuP+Gs5Kvk+86vOlfAfjVTYR7ULbC1ZTwHApI3RO5J58HIJKQZ/M9kDOZHE7CmugpxPG6Sy8uHHF0GTRIXtzQEgUu5g39jZKEeQLAk1fKkUii0tmEavcGYBNRQMuIMRzVPT9WI4Xvjw5dSr/NwgA9DosMnu0B61cN/8kxoV9yyA9u4raCSKCHHJrUQcgAvZE4onrqjdWugzuIWHiQdsTlvxAAYDaikTyVLdjF9lvkZakMzraUFfxBNRy3pI5iApA8dlckRBcuCAsI5Da7Gd0E6UoGlTgBbyxLayBU1X1P+dtm7cW8/3zdJBwQISmIjZYW4aZt6ZZvMv4EAL9636p9i2yVL6rqLTvHjPBdyvmEbC8X90WEYbGcMkxCJjEkk2pDyz8C3z2hXRdqTZh1G+JtUf9AN/d9ckAst6oaB5R83nBaohGaNyrwa4lMjakBohh3vB+4Mh7hcZPoCDJM2QDyNZhDJbY7lXz+Vh5K/jTm/i5UzfMUb6EDasLQ/Ikwxpcm9R/wReFhxKaRYtOL9K+MVFY6LR+8/022PSADK26Bt7uaEXBSJxgCEwXD2Q2WmhN4o/gNUPb2a3kUswzz4zv6TvmKvhCoE1C15eAVU73hqjl3wR5G65850+IgAgbIt0meRFmFZHu5WbXwop6YeVv9Zn6X2RUcCCEMxfw3WTFytGH9WRAUaY/eaGPvY8PzSEAurOFPt6ylPjzr4JMtFQ39zXD76huFeBWWvipTExqQ+P6UNAmob4y/1xggyoQVtbZHCWV8RRl1ejKFzd8vmDFpGD8u/k5EAr7yubZyhSAZhV0uL+4lULJCpSmo8oL8HYmMCTZENQSR95f0K6FuGoZr1n+TXAJ7NbMKGaxmXTrGiap9krRFyyOGNwC68ejePQmIVvQNNxE1zwDJh2hdtcf5OfScNtJZJGDawYUoFyBdVwLNgUdcbenf9bP1JNqR6meZp/uZrJkGizYtgoLFeiJ9nFhf1sltvR2St9Ak3X1KDQwVp7XFjCJfThJldRtIIrrodbxZyqJxqLuqLOmkRY07AvqgilQbIDkVUU+mO4WPSNc45/0ifD2Xb7rqIxlDkhTWO8DC7G0cidAjT8YAkNbcCwpDtUabsuNRbzhz1BX7Amib3Ed2HuG7AhNzZJGzYNX7xKg+RIMW4P5KcPiA7R7vCSCAIpO3CMaRAruFEFqzzIg4xNG2PDMA7KmlR1GRDu8ZixcFXU2sdevCyE1FH+GBOZWfWxIf4lu+/eAESFJWqQEFr0E9+qn6WtUyYSDcDY0kZ+4QEsv9IBuNWYNxxwh7yRmgQHE+hwAH3Dxo2vCzcMrhvINMBugGCvXLfxYjHv0EC6WFcsqcChFOh6bmOZC1xM/6EpsSs71+MdoJYc//JyGMHM4vmzN74FxpvdvY5ByGwehrYSbhBsTbQBFqF1hju0jy729GqAN5ndZTS3vLlrgJa3/5zvdzoN8Lbskd0TEDiNtWVCfrZBOAk0vdKtYxcRxMzypU7MjTIfcUmFoMOJiEf1erWARwvUdKuE5JVmZh3BDcnEQGIYkXdWVh+LXKGDC/8DuEd/kaN3mDoDd8ER17e5iSHXdy137ybJitndifzTURQT2GwohDNxjBErkH8mR+mzDDiViEV1UGSpgwJFYRpWng7bUhx1JQB5Vc3pdfo1zVc7gOSjKQCouAIuZT0A8uzNWN2gJiDWh/WB1exzLFWJnhfEs3HuTH3SDzMQ3jPG/M0M50J3scqs6R2lGJxK+/YBxY36om5vbcq2FJkkvnTSoJAEKFy+s/lbaTjPoqXiwY49R3LNhmCXMD2TnS50I9onox4afhhJLYiQfLvsS2LkWhbkBm+MrTf08EvjV33uiDcQcIdrZEVk8xRB4UzEZ3HbjGRT5PZ/Ky4MxzYlXvGWPYW3bpf5Vn88L96yp/AWQ4jvLrORKm0ooDa5/d5o1F+TyVd2UhcVBpS+BMXCmDHKAzSHoUFKcCVQsDNmT8VVL7zLbO2wPWH4Iyj/rEwrmYEJYrze/cRaVYNMjhcNQqCrBKImNRZ2ev2BiLcmEAnH/eHwgab60A6GR63cKMCHYFz67q3gc9gguaHnJuJ4nG8NqqDaFIm6I1F/TaAyAxkqgoqZTum8zfuEyRENbs+HviCp+rAtM8eUhT/tmGOTsYCNtDlYeFoefIVLOzhA1JiUK4SJ2b/gaJq9ihSMfREDDRHrS5V8k0416g1GvdEaSa7pN2CBtwVXNxVtlVdIu8f8m4kNssQicK325nKVmApmLApcIdpp8QyQxMVVc1JyhNAE8ozK61YJuYmb8gF/7++CJCoVIy7WrisVcrIzhBfWxNSrMkEwh5J9t0t1Oj3OgDvmrInsUw2GhWX2TbsGSqO4ee5MK/kjG3ikGhnGJjYb5FicBkqLIkt5NZ3lyJ237mxanyw9K0HIrfoiobA76K+NMUo7llsz0YHQbHgsszWMN1+kTJsWYRDh2Vd57DC4tGAYRxf0yezO5NYf65M3YWxyZnhEYo4YVx8d0CfRZlKaB4lqn132IjrhWPKiw0xjpOEA4dGoL2UugoRcCbQeNRqJON2uoLsm4iDhgz1oLRBlFINaS3DdGsvfm9TTr1DFnV/MjV7T516gKklFoaX+Zs88yGaMmtIcbDb2TqgFsyQSkhVff7zC6G1fLv1tJZB4QXeJhANOT02iecG/XA4euZVHGNAo4FEwEVcJD7O/2dMGHjyiTviQ6E/u1agYQ+H2qT6fvynmCddm0C+tAs8UEbZDFmMEN46lw2zpIw+Qh0rxgraOd+40RCc0sBrhqICm5KsQXupRfX1Uv3OdvPmm67bgR32LayxMswRTFn1tlhtfuwtM27g/m9l6g6Rs44UxM14Jqn7Vq/m8Tqe/JutaIYWSp3uaXxpB3Q3WxBbEhRmX8pFI8ayzZHiyBH83vqWszjpLUid764G3PJGzzpLHWV9pkwHVC7q/u8lTE1Fpvdh88dNWXjKl/NYIPcytCIlMrN6s94EPvPiA1fyotPwmNeiKhsLOWE0WKTP3UyGDQcF55cRVsCRR2cEk9kPWBHM/zMRgbkaYHiotP6iG3WF3xB2O1bT8VvVXzWdPtpxkVToUY2ZDn3xCJBi/gmONz+XHgRszCbW5H1FkpFLAFoaqhjyRWCRa45ovtLSeO/0fLSf5golG4oItH3I1l0rvpaWKByymtEiSs8xstwuXGo54Y/4mv1a7vsuz85khqUI9Cjn3rtryExWrThxabKJijQnb0hIVK0pULCRRtn5EpVNwg1TjcUbDTu0HYVw1HkT54haHFbQgic4Ki8qlLOQevvJFLMoVrrAtVlEJ0h413OR2+oNaU+2apVybpWBMqKr2hVm1okF567oXUt9aal5UgpIX9G9XNBiJ1mzqtcbgS4IUq3ZhacFW9aFC6oer0YN264kNSorhJLAQOMF8px8q1RTCYEA+tP6GXfmNouobTIyyfL0jTVUcMlvLxoO9fP9LfT3NVspSEKgOATVlpkizFIJtlQQUiRijElkvIAChoNk3DC8LX8qTDeE8Or6hwGTrPPWW2hLMjyLXliDmXOeur1gRghh6neuQVkwgqHPWm1Ui6IsBAGxhqGeZUFQpwlhYEt+l+QHrQLAgj9z+ujH20FIXgqpCmFavXwBv/YVUG0JcYfreBTuw/JM7+kCaskktqWtCL+ahwyzJjBcdLqSakQODevDeTAQvTsri3vK07L6TPbEif4zWUeosMVfDzUgsClVuxnLESr+Dod8a5SDhEMBKuCIYAV2mzA1Kjgk5v0wkhvnFkookjAJ0KNWLVCFLwldAdLU1NpkDmPYz2llJLhWvLlnGZlWAS0nylm1kXMXwCo9PjUajgbA38O7idNAEmBSPW4JL0qtbo9aULky84nsu+bhIYRwpclxuBt1d1gUUf4CkYO6RwpntVFcX+8ANglOm1uK7nDxtqihhykTg0ggjc9H65HWQSHjgx/YrOfBERIDgd034SVrjveAVfuPkyVWMH2ZB1Dgsm1Gx/UaB6R12ASLLgSdF30lRshiMO4jVMyfnsy8eHmoK9fhBenO6XDFvTaoLmp3ZhOjsGxzQ1wEBzKWgPrixpw8sUyoS5SNTK0T4/dtUtRYT1ydG0Cox8JzSfrO7g4BQzIJUWADGA7K8ZmiffzhDGSDWaAJKmVA/S3R90aFFL5vOdb5EsS5OyYHAU/EXKVuaIjSoZAhbCr3Eq8jKh5AbEu1+og4v/G4+f4o+P8Y+48wmZEU0smvDcgAl30ZhHpknU9ci4QznkWrlmdPih9WWVqm0aWWjoyeg+jTN7Xb6ajKC8GiG+R3j3gZ32tDZ5TYe4tfZjuQO7qGIwODJ6P9gZrcvs50WadyLbUfajsggBL5m9I0bD14D4rDXsI+i47WdiFP3+WEaXwg0bHwZgDA4vAYYisEtZ1Bu8Plh/Tbo1MAAV/mYcLb0STzznRiQyh4QqooB51f1ufvZtSn8nB3Qtif9+t40Am7gNZygLTITEWX9mTv7zW2gSoUYAG6vFLFYRKhQKGSG7HJBWAW3uZyaTUGWoC9SeRBMo556hvEEbxZEsLLEOrH1gyHj+SpIM4VMbxaYgTyZc+OGYs0du40OU/nv7He3cG3PprOPd4r1DKTnrGmZpGksDJL+pmBctckKou6gHGIUZLkPXdoMZUn2FaAsyqcol0xBIdxsFInp4VkzcySV9pPztguhLZbYYZg2fRdOmnRbDAEx3ZiyXGMuTw5b1uce6GuTRck98iuLxkGxGCjaDt5ihZDwTJFvEf9jmFkcIUnczMQAObzzLyLumlaOZKsoyFLmTDjE1oBxb5PRcrwBLJd0w7gNJG2+Et1qUsP+cDjkjtVEt+g6gY6j703kb/frWOm1ou5D900uC04WTX1yHLnN/gPqjCRuCy7KkD54D1Wg9ZfypxZBu4Xjw6+NMc0nC7d57SEtBQvsIyx2H2Uf9AOLYBlbi+i+Z4RdfPab28Lx2wHMLYbvYHKgC7mNXWPoKpraxRIA83CPC8viA+KMAtGeKTh++zkIl8xtju1xsZP7TPL9Gm51bmUYI91mNvCGA/1idXfxbd8omj2ATM/v4Bck4NWkWaPCy4QYJnizuvMTT7E8CPDxZYy6z9/9Ltc/gjIW+xxn9toa5k2xauisoMcYVxJ2dzP700LAYd+6W9HTrzD4cnmCBfULrQZuwcEAlspiF4uL3UwJEPXYJ421ZYzwO5jjMzzpJ9VUH1hFp+j6aCVkC6oRd9Tt9QcrmURFTeryRVJEC2u4w6z5HGMTmWLX8p8tJz692KKi2b0FtLwLLSfq9DcD+OnSqVf1f2EN2ANmYccHrb+py049z228zo5vAIDYo/N1+vqSAQSIHqH28Ow+ZgSKGs4AihPNZ+vMqt5s5LMn61hVZ4ypkfqIQs9FYLJuWnWqAa8zEvCHKvjPCSV4MMJrUIMe2MCKyt6QRIYp2EwotM5dOg5MH/aFnS53pKnG6akEm7wIxLeH9/X0A8ytW1wm51X+Kcj8/VSxporFuYPeaDjs9da4OKz+U8VszmBTzB+uZMWvajZej0cCCH4f/SHSC4KMsbAEfKOKBUVjfqc/UG0AWkNpNQe7g3pf8uGfvuSDDabgZQt7XMGgz1cttpUUfLDDtvdVIX6QqhA20MYT83rd4Ui1MQ4NpTUhytKH94UjfpjCETYwh3PzRZzOGIhHVZ5bubIRdrznn6/CRFnwIKA1dyjapEXe6oLYV5koe1XeF6X4MYtSVDwTlNlC0QBIbdWecLniFHYC9fs6Fn+7OhZlDwalYK8n5ok1NVV7ie1qWdjd3vc1L97XvPjnrXlhf0+w7KInFnS6POFqhRPJdmknkLyvffG+9gXFa1US4SQsARQMhjzuJi0YezsUZNb08ij4k6i2cTgM2DJRt3MFPd5AVHsrGMju9bKQ+DlW+TgUrvKmAboRjzsYdTvdbwVduXxIWej+o9YY+elXAam+DojNecGZN3m9oHVrVSaqNVQoAmJz+P8gJUMq7Qp5f9DlCrp8gWq1qaoLh9jpV++rjrxb1ZG3ADscqTeqxfxuX7VYX64UiR29e1+15KdTtaTswSGzi7pdmtddrRuptHCJnWv251rdxGb76CWNhdwhX7VFNhtKz68sCP9x6p/Y7ArpS8DpjHgCVfsgSoqf2JlmfoYVUmx2jtDzRLVQ1ckVDUXlUey56k+jgErxWmGzsYg3qHnD1bKiakqn2EDgZ1xxpSqQAKBdmhYOaqFgtYA+rACLHZR//kVbDocL8taAFvGEXdFqyd9hBVzsqOE/WdGXw4EEcA/FYp6A118titsWgLGD9ftCMT9KoRj7A2AhDFrU6W+qWuOUCsXYcb+fbR0Zy85ZsE4wGghXG8vbUK58jC0M31eaqRZ8GL4ZDvj90VC1B1Gu2IwdLfr51KUpu21070Yi7rA7WnUwjF1pGjvrxD92CRv7fTJl3hf1+5qqBleZEjZ2EHtf7aYayKHW5vNoYXfVluSqC97YHMpPulhO9TtDE0owFnZX/Tm/hkMK6NiB6u9TcuewlbI7q/k1p7daX5598R2bHf+dqvSUWSBs1O9yBZ2at1pt6G3L9NiB4G9Y6eet14sQaXIHgwF/rHqIVFMEyB4Qf8fyQdUuHCXXWCjkDVVtMCytY1PW5vO+6tC7VR2ygTFGVkaDzkhT1P+2gsYhR/W+NNFhpYnsQYn2Ux9Q13D1gZAl2e9lDR4/1/pFNjBAlc3nCblcWuwtnDl2xYvKuHTe1zl6X+fofZ2j93WO/pHqHJWlcRgT5A07Y65g+Ienlu8LI/0zFEYqj1uutyyY1FBaG8lOonlfQOmnXEDJ5hBR2Qh4/S7NWa3hQK6eZCeGvS+u9L640vviSu+LK/2NiitZ6BGLNHd6YtEQRXX9jz/8fxqjiXZo8AAA"""

def main():
    root = os.getcwd()
    kb_dir = os.path.join(root, "assets", "knowledge")
    os.makedirs(kb_dir, exist_ok=True)

    if not DATA:
        print("❌ DATA 为空！请确保数据已正确嵌入。")
        return

    print("📦 解压种子数据...")
    raw = base64.b64decode(DATA)
    decompressed = gzip.decompress(raw)
    entries = json.loads(decompressed)

    def _segment(text):
        try:
            import jieba
            return " ".join(jieba.lcut(text)) + " " + text
        except ImportError:
            return text

    def _chunk_text(text, chunk_size=500):
        sections = re.split(r'(?=^## )', text, flags=re.MULTILINE)
        chunks = []
        for section in sections:
            section = section.strip()
            if not section:
                continue
            if len(section) <= chunk_size:
                summary = section[:120].replace("\n", " ").strip()
                chunks.append({"text": section, "summary": summary[:120]})
            else:
                sentences = re.split(r'(?<=[。！？])\s*', section)
                current = ""
                for sn in sentences:
                    if len(current) + len(sn) > chunk_size and current:
                        summary = current[:120].replace("\n", " ").strip()
                        chunks.append({"text": current, "summary": summary[:120]})
                        current = sn
                    else:
                        current += sn
                if current:
                    summary = current[:120].replace("\n", " ").strip()
                    chunks.append({"text": current, "summary": summary[:120]})
        return chunks

    all_texts, all_ids, all_metadatas = [], [], []
    for entry in entries:
        content = entry.get("content", "")
        source = entry.get("source", "unknown")
        if not content:
            continue
        for ci, ck in enumerate(_chunk_text(content)):
            uid = f"{source}_{ci}_{hashlib.md5(ck['text'].encode()).hexdigest()[:8]}"
            if uid not in all_ids:
                all_texts.append(ck["text"])
                all_ids.append(uid)
                all_metadatas.append({"source": source, "summary": ck["summary"][:120], "index": ci})

    print(f"✂️  分割后共 {len(all_texts)} 个文本块")

    # Connect to ChromaDB
    client = chromadb.PersistentClient(path=kb_dir)
    try:
        col = client.get_collection("coze_doc_knowledge")
        existing = col.get()
        existing_ids = set(existing["ids"])
        existing_docs = existing["documents"]
        print(f"📋 现有集合: {col.count()} 条")
    except Exception:
        col = client.create_collection("coze_doc_knowledge", metadata={"hnsw:space": "cosine"})
        existing_ids = set()
        existing_docs = []
        print(f"📋 新建集合")

    # Filter out existing
    new_texts, new_ids, new_metadatas = [], [], []
    for i, uid in enumerate(all_ids):
        if uid not in existing_ids:
            new_texts.append(all_texts[i])
            new_ids.append(uid)
            new_metadatas.append(all_metadatas[i])

    print(f"🆕 需新增: {len(new_ids)} 条")
    if not new_ids:
        print("✅ 所有数据已存在，无需追加")
        return

    from sklearn.feature_extraction.text import TfidfVectorizer

    # Retrain vectorizer with ALL documents
    print("🔧 分词中...")
    all_docs = list(existing_docs) + new_texts
    all_segs = [_segment(t) for t in all_docs]
    new_segs = [_segment(t) for t in new_texts]

    print("📐 训练 TF-IDF 向量化器...")
    vec = TfidfVectorizer(max_features=5000)
    vec.fit(all_segs)
    with open(os.path.join(kb_dir, "vectorizer.pkl"), "wb") as f:
        pickle.dump(vec, f)

    print("📊 生成向量...")
    new_embeddings = vec.transform(new_segs).toarray().tolist()

    for i in range(0, len(new_texts), 100):
        end = min(i + 100, len(new_texts))
        col.add(
            ids=new_ids[i:end],
            embeddings=new_embeddings[i:end],
            documents=new_texts[i:end],
            metadatas=new_metadatas[i:end]
        )

    print(f"\n✅ 导入完成！新增 {len(new_ids)} 条，集合总计 {col.count()} 条")


if __name__ == "__main__":
    main()