# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "numpy",
#   "pandas",
#   "plotly>=6.9",
#   "pyarrow>=23.0.1",
# ]
# ///
"""Portable, prediction-only underwriter model review.

Copy this file anywhere and run it with ``uv run`` or import ``build_report``.
It contains the model-neutral report runtime and has no repository dependency.
"""

from __future__ import annotations

import argparse
import base64 as _base64
import sys as _sys
import tomllib
import types as _types
import zlib as _zlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd

SOURCE_SHA256 = "0e3c6ff3ba97fad6899e08bbd7138ef7c4472b677949fa6d05aacf10a8941a51"
_RUNTIME_PREFIX = "_portable_underwriter_0e3c6ff3ba97"
# fmt: off
_EMBEDDED_SOURCES = {
    '_portable_underwriter_0e3c6ff3ba97.reporting._underwriter_styles': (
        'c-'
        'pmF{ch{F75_g^!6hgVca|s1A2)H(VO!B*16FM4?fw{wqM#+pW+O`iCC5&SzQ!JB53?uPIsA}FigJ?MtQXCVk16te'
        '{>}$=udlDaVRa?is5+G_BVT^}NNT|kyyZ`<A$cW8yJw_nX_?WYDj7MJ851YLTPDa~zWw@dv+L{YtE+Fm`p4hD`Sy'
        'oD{qf^hKj0o;5P|fKsH&Fyd__oF6_tpZbk7cKLkhmzw+}#$qU~-'
        '&Zt@TLT}~CDrX?$oCjV2kmYrK5&GTfD+$qxG*s=_0>(x5@u-1E30+<707H1zaW)q{P6;+96-'
        'KF=dd%f>YaM(law)A$sjHhJ2yoVnv_z};NWTH1Hj==Iwe80ZWXitioDo3WWEu*<UOGuWod9qCO36-'
        'Gb4j<p<YZ@nt_{@r;I-'
        '!iqY_VcC(UReg&SSkxUZuyz<DuEp3^$S7FXmISSWO8E5zppp&3bbbIZfgCCn|2WYTd8k?`>NkgZa9*fuI>bHc@lf'
        'kY#;#Xa|sRZD>u6Tg<Ihijr)|ol9A4$UJdLOCWVS@v^B|+JcXqc-HPWWU-F%yI-'
        '!ZKA)1$H=8X3XJqnMnxpgmOt#fIYWPna&8n>oqz3}e?At>j{qDd^vt#_AKkpg3ADkY?pCN5a)5o2tz_X2_w!4Wud'
        'Rt}Ba+{1dbwQsuBrn+c;pKg^r#(_BIC>dDtQ^34;DM}7CH==^)AIZ|N~^MEB|MVCPbTC>RP1=EcdcobN%4&CswXC'
        'L={xk;Ru`Dp5oc%^K$4nQc-'
        '(wZpMN)>ElEV{x&SA5Zh*%r`BTBm$FFJnQGWh2teukUk8D>l^3T6sPf0^d@Cqh)uGDjE+o}XIE5LSB!pr&y;jRzi'
        '<sMeH(jM+gsZyh@MXW^YWQ{?AiezG8UY|)*6+AN%O8TT<qMg%7+qv%~tRdI;N3{if8-'
        '8tj&sWIa__h<2SP8t@qruQst;IKt<w?G_R?!sUcCc*CvV37J11F^00#N#Ak{(5a{FYT4QN#_FJ&+2*inrjT@ocrS'
        ')V`7M5k2vS!{bveluwn$^NHWJbjtzp&tF`}*WbI}N-'
        'I{!7JLTqBk^n`mrB*@B~g{<4Qu5}soU@NJj+=5J&4nVSBWX+H~fGpiI&QDX5gcMb^wp^#JXxAJAqV0u!5rE9_#=`'
        'NJoM;7TE0;;~cR)2D?o{!E0PGrA2zHqL)M@Sz60qT4JJB$E9I=OU0DTWSE~@{Pa3Bad4x@h8?XtUsE_cagLIkqXH'
        'r-'
        '7~K#sUK4~H_4JmtC&o%EjJ6f{%i%)6nZs~r5Db4s=dH>nEZA!WnR|N&vD<)Obl!MshDTgXNo)X#ba1zji{Ur{Yz$'
        '<+yvD!_m|OlID~2vWfDb9MTyce*nXn%)I)-vCt1q1BKz?-'
        '6npww^b15by)Pt570*U?Wb}qdcS@b>D4uPdcXS8v25@<^N>0r2PThLd?Yt13)p4Te0&Et@s$cInO0r&U!`q4K7zi'
        'lNB>_rMdUEk)VgfkCljLX3qIAGxMeRfm3w^dbuaw9xNZf}x{7Q3q@^yi!xg@Q-'
        '?gvIP5fG(r~^wcj=hMpcFe<|8U3h#aKV}(HFe`AiH-D%tGDKrHdbwiljF^ol&;~z1iw!HxWg<wydogztu{f-'
        'S*<SGp*p$K^B_K~+y;45hjQy+$LMl++V=+%-'
        'w<S!EKz%J9qqcbj8s)PmKI37y35PP4}<d98X0uV=P;FD%{qLhOB^(83xL18P_)o6uYZL@}FOf~=-U|o2X8-'
        'h6SM?&imY^53eO+vPi4CrW3d9lkYcMdGSD%&_Gx+t-'
        'N=U_+Eju?}~fg}3r<TAhyVBK3j#L@we0ay>=wrUJt<purr_;b9182GYf&kNoyk2oH{RL@Z^=z+<2l|upfQ6A`oC8'
        'D-$+d?s`z8q{iNF%CkqUVlaz-`F6?Te~tbg0jLH>7<dYO8wV`h_C(t_J;e#@I5%X-'
        'j2wE17dpPFf#2PC(u{?&KD#kk1Z~-'
        '(ZE>%??+YEL3FNsnE0zg=f4_GPy<8auD4$=I2NmtU(a28EtQqDJm4Wyv5N)E+&&M{8qZgb`A*^RZcXm$H1-'
        'A*01ZhCIO}(y1WFtEvoc!G&d8+3>uDQM(%RvY`zK|Bqu;4M`@rkPU85Ns&Q!fe1e9Sy-'
        ';XrzLFqciN_bTZy0UnBN)1U?#E@9C7=5y#?7SHnpPxMzUJ|;kgcJAraNj-Is9sNV6EV3gTpgjqV)raJ`lS{@7^yr'
        '_NU82Ynb}{>N7lRQPJQ?BbS83&2IAJ<*-'
        'OtTa~XusBW1XsiHao6A30KEH*lL3gl~Bf7n{g&DhJZoAD>Wf8i8~L)MmSJK?IWl3^L_pq{0Vs8qOblQLGc^iAG4^'
        '!M;VV9kLap-'
        '<ZDo@jAYNkb_O(o1gX?BxhtX<G%lpOL84Nl&KQaR+hoS124pu7D2Ufpu`c_g<l+MZv0(iC47donBua708I1hwHoE'
        'd0htfi3dyz1Sa2F=mPF@bzh43==Kow$^iyjd+IX8Ps(2F;!Rk!ntF9uMYexHqbjSByuS`F-'
        'Y;CKYylRgRM5}p!o&gsGr{i02L-JgCTlzSo9y-RsR-DqjvzqJ&nydOtHD9-'
        'zE{7dWNrn%Ru%Zgn%*iMWVbIB3N?(m0s?)vJf(&C0#b007o2*ITHFqBOUdThP0mFl2Mt9wl*#@UPO-TxSgwbVhbm'
        ')WwA}&Rpa~8HOkjmD;XNkVLoTf8gz@0yZoC;18t`7tL;T7q${1&xf?9fYxlncrJ>@h|7bk4;0!UwjL8r@FK$b|BF'
        'T*A)+_~ZT&{pyE5jev-'
        '!VX^BuE9yB8`#cX1>Is23FRq&?Z|w^XOH}zbd80PeR%ohRWbLmJ5Dl}Ef>o;jOs);*5v**iAmqCPTrwE7)$Nu#-'
        'pydnW?>4Z?6pzys&AX@tV^#nKH<GEwG~Cb;ISf{Imxvt5GGcSF_D=Yiu^A4bE6gc>!6N3T0O3T4QK;YYTm)>0EEn'
        'Ehrj5PO@9oU3skoNE@chOxOSY_kXV6(lz-aeOJ|Z8{@lKU@#4p*&zO6`3K#@Su_YTi1gzHL4S(mbrXhYC%3tC`Hc'
        'LQm<tyKW(`p0rUy!^1ZUGznHDFX2F35{$*z86H;{A+QeT8rbn!-'
        '|Z|~iReal?!O`twt%VeEC=g8vC8Q$N8FtMt&T+Y}hk={6*=D2N9JOo6&-^=r`M2E_y%cu{YMpr%b4UlJqk>F)-'
        '9}Mz+k;#}=y1R3$6dYNp1}1?HY7EnYh=%ICkpd~ZMg@E7p(zxzcA&`_x(PHjXzq8)INg;M^bu(jnxZ+Q7T5OHta)'
        '@tuNbz|-AYdO{fAFflwi}QQ?7mV*jj(8;sBsvP(|LPd6FdRw%=TL6l}-J%o>-'
        'BXX%R`yI8*LvGb)jraBMCpwg|qD~oqRhYM-aQ3dcUo-dZmgEwh<e@WbdOWa+rU)Idp>iqo%$F<Xmw&}k2Y`o5Y=w'
        'MA^Sbwtm@)vK5(Q(F`gVEfP^+UkUib>$oDWlDvecG+lNP%GYJw~GzUwC8Lnv2>lcX#b%m$>g@$GuI#)q{s=rafch'
        'n;MH)!iq`wPbU(|DsD3I=ZydNcZB-FbL_S~klmNV>`qMHhyY)q$uSxUXjYXT{cUMSSAg#gtyP;FT4<x398qWyZWz'
        'T^kAg!IOf^po+ptKcu~(aW9>*8V+sAfdS`Xjk%U7BF{-'
        'Vim*30>Pm4AY<@io&A*?PS1`1Mu}EB2LdKMkJdZPCxcIxt`R^R%QRbUp7X4sEEW>u<Pxa;KObAgk{qCp8JkN|LY$'
        'q_Zt;7$$<zdkv3K(^0$E)?=46;aSm8d_87X9Kd1@dXLKEfeD_<7pRT}6-'
        'a0v0^_T3Fs}u;LsZipB)TKi6zx&4P)B$*qi2q<QbBF=2n)=c9p*J<|NRUpgT4_lYn6;hoP^i^#6&e%Zvb-mgeG8y'
        'p+X?HOR|(385^j#QJkShU~Va8Qg#CYRl@Wh4vlT+8j=2RU{LpwTf2Zv@ZHOa^jGhC$aw*GrBSWlMcP9>=Yr-'
        '`ZWRpCskPc%lU<5cSpAaOv7GRpvLvkq%b94fzC5NZiw>0;3gKrZ_SoCd@D(9VDypK0wro$IIJ&>Qcd*Wrt7yp&RM'
        'pi-LDdoQERN@g=E7Qh<6r%j0(7F52aDy)68u#=qulr}1pWtx@WPq'
    ),
    '_portable_underwriter_0e3c6ff3ba97.reporting.inputs': (
        'c-'
        'oy>ZExea5&o`U!P6(H^%|R?cWvEhap`Vy4Z1HuHhVoF2n1Q89bWZTQF7LsroX*2LsAm;V(0E~z}n<+_;C2laAq9W'
        'b+7WWsaag)brr?6WKo{5U6hI>szs5rO;NFEyRG;(syVB8SyZ*iw@cS`9cNP&84JTrQ#Tb4Lnbnu1{HZx({ib0;v!'
        '9XOe4!^9UH+9QCWhr1^dkZ)9^gzN*cC~;xv+yOC#A1DTy+wA5yV4v)AxdP1Ji-XvWX;{erz0HLs%7ar9u`WaXYkl'
        'I5itD&f#D0RNYX<6Kw8I_25zzT_-0%kSJxr9kf81#>0e@k-'
        'S6dEHcb7#Fg3@13_r+GP2s>gOnJ0DZt@U9tbR=eygaMO5FzNM0^s&#H>{@TE+apFtg$us$oJO2{Jrl8bu09!_*%w'
        'e#Wpm+-^+)yMGS^77*CZTQp8)w}Te)78h@&!Fr3lT(uT{N?8I{Ov_}{>#<pZuaDd*Nzij-+cP}`-'
        '>0ZyNk>7FYj+*`d=3}D|1tK0B6DUAp-W~F!--'
        '$nH4)(zFw%&)<i3I+75QMLecLR&a>k<bg}G9p783iLUZ2`%`U2{sJxpduSLe`i@#D@T=ymtk|*r(f#)n@b=AoF5t'
        'cmcHAPuWBxGyO%Bo13m?w&|&W|mXJYdW>o(H#8!~HoBpGsnFyYV|A%M{FxZesib{Um-UL<~2M{!-'
        '+|Q`DZgv=(*BS9F~LbFV8ABTus;;VH=O1b=i%u2kd;fyf|kQ?X|~rSp;VMDVaI9(lD=*8+U_i2Dchj}j}&@ZT#Ya'
        '^w?G0LPM|0mWe|Hg&iba6U8rnx^BX+VR1Jnn?s4L981*v?Xw=1+rqtGoDYXt#}I7+5ss5Gt7(@!#9p$2$kCsf6>5'
        'N{|MJbQ3IB!48hi^h#@|W^i7IOuv!c3&!>M?uthGiCJSSprlAzyc&AETV8S;L>Pj$v2%>cudXlFbpS^lRmR1C5Zy'
        'G%prkC_(i6$#OzZDT1hU8S7Xh+FH$ZJN?L($(=>M|fWk~uH(S3E1ht1NA_SD!khU*v4YpO5TmX);^4UcO+)wHFN7'
        '-jT9{M2s{xsJJZB9Zy1wuZQ6WK|idJw<(?91sGzE9iUyR{ZO(7B(4h~feLVyI}t%NWuAp7IPs5J6=Ah;%|>;49F<'
        'vVf%+-RvS=34>5CwBS3sEX?!idxOrtw{3Ak2=9ah@wM-Inzx`)pwkh2ro>$HatV_zO+9Es;y+qo2j+=V?j3_`>CE'
        '((oS4x`Xez=}e{$x#>@3XH>0Pr|n?xkDQQ)wdi{p1Pu_upl$|mYfbS7*WXo(M~`cZ5hT>xQ`QSg^m(J!VzjDhevx'
        'YFfjS(dE*%faw$zIRA**a8}cLpHtrK*dTuW~$|)Rgfdj>c!ON2J2xgwN%4gRfp~W*HAIAnZX(fPq!wzIAF9JGJ-'
        '(jxd{Xviiwm1ZQ;^IfhC$gs(p&sj=hCQLb54n5nOng1^CicUJ?Ue&|bxRb*ELodweNp1vP_`$5EPqW_?2VmaLgCN'
        '()W~`x`?^OC-J13ruL=Y-!)8F?TFN_2m?j)FF$y^I&Wh8MzN#i#SEYT<*wFwzi=m?tr3X2sq&sfTYd;_d89-'
        '+pWkN^UFt==y8Pme}M!lE~?s)l;poOm#>HHDi&XQO4zRl^Tvy(2lqpZ3EgtZ5UayMu7184jz5)KMA^;W|1a8$p~u'
        'jqY-'
        'J)$O6mB8>Jw_jQz2brXDciL<^kGmVC1NY8gA;I^?yZOJp6uRLO4$@XaUnJi&X|Fi|DNKSzs@@ui8Kp(Ol`u+X`N!'
        '>t_iQ5|A8xCnqN&TK4zZkHsVbhHN{+b(B=b<&z5|Gt6~t#%A5guHq#Kl^eMx15s(6$kBv>ldry-'
        '05;UgE@hdQKbvCWIhNF1}r&#EcH6J-'
        'tRo9Mc5gWFEPg=pVI>8e+*>lzR4L3Kk0$LIvrAr#n=f(?(b;{vPercAk7yId~shec0=l}ZdnrX1-'
        'QNXeI)iLPz4k=%l%%T6#N)k!h6LBgU6cRa350G}|EN~`F3T`{|PqNZ|Mf(LZS9lI@+>A{u8X%L9_VhD(+_gmLQ1Y'
        '@Zn%BfKEPre`IL`oPvG=mZXu4~1fNauG||7|w8AnkBR-|h|1VHmJSlCT?~3Hoe6KI)s}fGiwQWK`;4NJ)9_!Jv-'
        '=_?fi#&UZYOgPVB;8hI{(b5Tl<aTe9_1NkNCbKCvVN`O?z4c57wwq8bQ>b-'
        'nR>?THF=^}@EL8(!;k$M{)oItf^3=k{>|N6#5RU1K#jqY`XH-'
        'A`IZZ^fAd0(@o@0GZWGH|HS_}!Go&iUG|9O%>Qjb{w{fXX`-'
        'Q;vtSR?n|5Tj=i7Y+p)y#evu~PE5$0cF3eeMEM1E7Y^LCOJakZgBF=KYO7UWwl-LZ1i_@0VwMLs^Yn~Qm81Sb9;!'
        '`jane>pDc#;9vLbBVVzFvaYlVOCOnO6`zHRz|4Ylr=IvC`Z*Pvs<&3pEqozMPGD0n^tCuvM}tGCs$C~TKtwmO8sU'
        'a7%;&}&f-H4K5Zk<is`)pn~0ZmNxiF8d?HPWbXysB1h4f;{ntx_#fDA!N@-7sf}4kto-'
        '9VCPWFsueqQiC~08bzMzHxCg6^-'
        'z)7SDzd=I)CX;M6&(((v%(1eT+sjC3$^ed0Ex9er~%qj+cR%q=Fs6S^;WO2Ee0M%{b1XoETo_*ip(QWd%|;QS7np'
        'Q?X<Rbi-'
        '2_}(GP&mx>dl`?P_}d)PPQgRbOP*&Po^ztUh#y(1CNN_sHH*zfLvF^l|SD*n4&s9J9A+<S7%#ag(e)ImRQq#b=1u'
        'LbIMI{4~l1@u!w&$F$h0=#hMTq2E*tbv+$RcqB5}f2~z}1HpM_tv}b3rhMyYd)REIf51>7`ACnN!gNZ-m5-'
        '30+%SZ+A`IQmzu*(B=I-+m2%BjP$Qm#!ufVKq-TfAXKW-'
        'K&SeKF%J7+WPA3!vDBgcTWQJGCbn%uJ|c_4_W+g&j0urnu6B<|$q*?iodW(zxxj;U>BbaRZpLuE+dZcNc%7ZorAR'
        'fXsM&!`1vHksGG6@zqXTqRSDvopW9q9v**-'
        '*T@@l}(<FS#4hb@F%~s4r##{W0ecNw`s8bu(p^1dA!n?tTu*frpk_ij7^0(n+<ZI7xXJf62q>WQVa!uEj9u|s{X+'
        'hqG6%(LOWxCBw<n|6b=(78j0FR9KtXa*I>NY41usmRjyryjV@R5q*(t7j%Ybpt6*H3wNtYN+R=U<9pbkaYh(7eSO'
        'yH&r+}1S$UO3Ti+l<kzYlCbIn@L;PZETYHcns<K_jlK{lIalIkCXcP)oIU1VA?t#zLqF`)I-'
        'afK$OGuuT8F!oSA6tQr17PEhfWIAHA1>peV+hHUKr5XpyVoq~}W{YeRE>nHhrq(0<GCes-Ifb6`?x!j3AuVMK6rJ'
        'y|9q-?fNfZNP&{7gU6i#)D-'
        'jzZR!e`8y?v!~HHdLCyL=#zD22cO6os3?~faYs7LyEqo{3IFOPRZ*%=TK6NGdhdf?*0q>;9cA#O-'
        'cWT#y+_TIdHoz{>iIFr&~v9=Wuk%lXKH^_umo1j?B*x?Ye6rp^oiYnc}jm)i3~<}(#g&><O2O~C#lllz~s`yEZa('
        '|2a`if_|E?UtRqg%'
    ),
    '_portable_underwriter_0e3c6ff3ba97.reporting.evidence': (
        'c-qxHYjfmAZr}AQ=t)(IOlBu*r*cUq9#__DIZ@rdvRdDzqMBk+GaQNM8FG%~?5<AHe-'
        'F@4pdTb9uYHxPE3by#jYgx<02+-'
        '(&t|h%)pc96chBnb)VIYxDL+=*vfh+QcRC*TRk=<2Ch0a!TW+6ii@r$O^4PR}Ro^Vm&R%SbV_&vi0!`~~U-'
        'V_NtNI?Q9-'
        '3{rPYS5GD>i+XR5gI<Z_BPss>9*b7uWkT`B>~vWzt;#se~&3b_T@?dV>8WO})Q^zv}LED7&O?+C#Cg{!(t|@bQS4'
        'X<Qd)v)SzIY}Yo2B+qxJ{?wLv4jl<tMO`<2(N_TI>`Z+-6#cENziIY+=pIWK#q~xvdR-ikFvfXuS^oKieaPBKfz7'
        '_?IzUL(G@s@$_Hqx{!5H?1Zc(2O*GM5%`=aj48=&(%d0!TLS*5=_T5zi4cWv|e?gJE<D)3R)c~t??5eC%i8yJBZ7'
        'xZ?#OA4UYQGYrX^%g$B|BqWuBP_rf$WQgQY(KRKFMnSC<K}m}-9KIz|N74hJIhslJoN^>^eln@y?*iE`Rf-KZ}Rg'
        'We>{KrA^(r}7eD0h-'
        'd?=<a5*;>E`NIe<BON)`HTO)xHN^?+1a_8wafBQ)P1!{R(e2JqV24P$@*C4n+Ce9%etRQn6o3YQ?bvt<*}><2whT'
        'aHmAc0`EQ%=n+?<{cRQF>UEbXm#~fG?IuTQCAi|J#&Aw{#;^w9;ZvX%kt<NrO)pz@*|9w?&JuJIZ3#@HW*g)Hxrm'
        'e8^+p_2n#Zec1g!KiKgaH9o)utjtg83?;O-'
        '@?7Me1Mu8JAPj=G~!b`dfkQ`Dgg_s_D8*SRCIMUDXj>XKnKdIzC~S$?Q{E-'
        'Q4y$EU4M~>=G7uTXr1`@)Fj^i8WKS#zw_{&uatcc1=xdAF8@KoDMn43?M15{to_yA&V7A8*NT4%yM%O0t1?yQKor'
        '${_52w)c)q5^4~pwE{cGG&fmXy`QhU2oBaLTKa$e3_vioh)5ZJqA6T82Z(sfN`VCgQ=QFlU?q{EIWOw)<A%tcR1J'
        'j80_vKDdutfs;%|cUby4jZ>%e~(wH21Qr!RneHuqv;?S!1C4hqC~o^0)7QIDa3aR_akJ8>ChmqgFOZtu%;kHb|{>'
        'th%LEs%p%$2)UyD1G!%Q^!^X$jA*~Vc=H4D76{b8lyz73QZn9$S9@fo2UfX@*8_;m{MGp%&R_i+-ADWS;o`-'
        'Aym@>1;o>D(N3su1A^AfJT9nt@osorLEL7LkzUuGvr`w_f0lY&UP6cpx(nuQFp<#etE{+{Y2B9?a%k$SS-'
        'T*qGL5u$msg7awF-'
        '3(8sgVIyf<=O=bnf20dix<dfuuL4U`CY8h@u%$HUkPLsC3M*UcPwu;`@tN7auOp`C#s6(qJeAnUmR}sA@&g4u2CW'
        'ir*zFF(7=`%^m>m<;DM;=ik4$^q|Jn88&+N{_Xd#&R>JA@yGM`LhjFYtu){6V10kRcn)nkVBQuPbD4azc>Zv9cJ}'
        'Yaf=gvjs}Jp|%+ACoFw<}tFB`!3bH5ZL-'
        '?hb|T!J~Z_yJn}h`+>l7{RI7FTwU&fXUUi#hv(k#MK~2y42>~RoAz3QgJP6%JFyrb}-'
        'Xm(L(F~bljJ+?P9TzjgZ%iwgQa|)?C#Cb+%a5f#KAG3NQnrMC<NNx!>m<m=Lz;*fwA!9&$8LmsW9GqEdRo-'
        '`A(MhW<M=0I>ZQ40L1wus1)I?K0Wzn?gcvb~~6)ie>V@$s1U*Fl+eF=(K1f@<$-LoRxiXT>|leIO3;}-'
        'r^@fh5^BUMfdRUb<^xscccBhERKbgWIxr#$D-'
        'P!*(^KUm?A=(Cv&}|SSw5`If^mVew1u+VS3awk?08nKftAjvcGM%mQY=DYB%MyE{Rq5y6g+AD?96i0l7>(o05&nv'
        'my2RF!mv<Lk-7K)LsLr&jqD98Pwt-<5k;^W#Vo`M6sN$0Np5^By-oDn0s2&;bIF=D#)ebLARFJCF=!FnOm-ORKA&'
        '%5k*^r0P%%^t<qT%E<;oH$fZU$L!7j=5QCZ?AYNdyI9~9d^%SBXVUv~r47;pl64-'
        'h@ZeDKMYMU3I%K>4FIt91t>9*Vzr+uGG{dTuPIh{Rfc9qpKT2J>RY^R~g6BY7pRov7dNUKdZ3i?a2&Zx-'
        'M`%KOS8&HjHb$wC_&e1!lQ1WZslr9s0qw1=ro3=R}$x=l(Q0@qJcfNPUq1xZs-'
        '~Fc&^exvpTH1@5sJdg>%EjRoPNL<gC_>*CCz6Y_RTIm&91qMjRVWUB`vPzZpHq$G01T}ADG;qrTly^XD@(o;(b1|'
        '_P=WK=49uExY^K`5mM!%v)(*qeSjSzt-&tGv@9dw#2bvoxX$v$rNYAJJzEM^tH#%i`mOT3|#92bW7FAaQMSI{Ou-'
        '8Bgm)rBUZQ99Z)O)n(I%P>YcuU(>5@Z=9)0sag=$Q~JmmsyjHa!~~?Y3%#wC5a7yI#+gX(13t(?dCGubeSKML|2{'
        '&=4Fs=GkoaQsSBv^;XEF252hruukz$Re!5#@eIu4?P){((CCInXgOG)6%ZbGqGD93`d2NwT~arFQgv0`i4~v9e&%'
        '|-'
        'nLD@W2^KS&&J;?AQ`aZgWm14l5N*JwmNO^xa))kvHqaTcy3~&#V@uGqmLU78>#sOfaB<u}$OYQ8geB&d7*(z4vjF'
        'S&(4_=xO90z4r9c=xL<^irfabD_{=?Q(16aTYLP;S8`D&dlfFiKPw@Xx5EBgGv?IAR_0D_8qNDakwNC3lsrk+2!s'
        '?OY9ZG>LInbxr7Tq8mt;$0weqtnf@VcIKLi@`ZCGrQ8`S}0y$cv6oGid6tUt16{~sV0B&Dhi#|h6(~n`7gpGArd^'
        'ASwcX@nWim4!`H;QLq%+~uL!L<)pD@z(eyUWa^O&)lZGmGPicNA+nX}X^OAwGEI1pXS#Sk{1c0kSQ(ege<tLJ=V0'
        'f58U8$=$T4z3}K4OXzWb+@?!mx~vvVIHOq76v({T}zsr+v|i&(bTQ#wL#np$b@zQ>FalWZ*Q`mg@%AXMWtHDJXh1'
        '>PM}rWG4SmGQrxK*v?La{ca)HZ<%Lr^47G(wx?g60a8nIPAxU+QFS_@C23&s*tNId;8o9OmT^HWGh5d{8^9!WEn1'
        'G9{cZ_hzd6IV$JYRav1jVog)3J$+DTd2KZ%)1Xufifk5gJomN*@$--'
        'woyMs{#3GEOTO(2`#f0*McnHsU7%rww}AM1Qlb^cT{QOc`xUKHKKxqk`bBPE{`U2)L4AU)rO0GqqEeQ7NvD_wBTi'
        '$b=w@wwz*<{C$-5G@ep$#$~q@l}bht3z(a7F@dNI71i1?IRAiOr5&=H)lDEQ#At!!-'
        'eUAs`=F$bKpJ^n!oPaHHs(_eiz261q^k1ua=m0q#(G$>R{C`3s$*%v$n&bpkIhjY_@olqIq5JHI)K+=c(ckJe2|J'
        '>4Kc_W@Y`;WrvqTX8<NCGO9^ss|3;#F;H|pez(}OpiwYhhd?YD?1{#q=suoc#?z}ESqRJCj3Jy~<9weqzI7U>8X`'
        'HAG_p$PpSwOfcNJQ>?a6<CW%0S_IP+X<N9xQkHmBVpmB9n^@jFE#8NC7$N3L*xN3dRUXUv_fNGHcuuiHz^Y5b}5z'
        '%}4JeE($C_QD8t*6n!vK!0|<Fu@cZ0WEC?2-'
        'hh?#mt)qVd6MxRF=L~0nHwQ?(;!8@rZuTH*KX()de!ERvw4+f+;*3i6KRhm4XzN!kPj$9D-'
        'PLOWCnyL7Mq8dZO@L?K)nen;fdYS9_s;BZop{o`!)@VV~Qv?O+~9r*noChE<Re9O9G_QA&FHdI7c0i2;_ry^P_#a'
        'YI`zP%_wLhU;!svL<VRaslMZZh~RjaL%t@`z4kXn;V8W?BRj!PM!#b&j>-'
        'uhi(a~4XYQw2X54wO3EIlTd)bxL^*43ZpSI=fK^<Cm9jeTgZSgF@2mt{My%nbea-O1#sy<-'
        'kcnBfAbuS9sGMRy(M06H^YN|TzpaB{WvR0;6*|BV8NE;w`6&}Of37c6n%E=+@o6Xg7o?OYkr8y-'
        '3gvDz6sCMKt8~l0=e;x0vblsNaQ8<5z6)aj<EYa&H_LR8<lDg%AnOo>Wy<=3Pl$#|Ta>Bq_N(2GgVl#m$0sC$8eD'
        'OS66!l%2J!VENT*J(DQ$MRQRtF|x#wbEigmKv3H9~v>4e>2L3J#y=07;nA2{sCmh}CcuRp0c*9uI2paElOb(VY%j'
        '6{wE7+oE+xnEZo+0Hc(D2*Fq%7k??+rc3vwn#T+j4Mv8nL`R%@BE~?DmpCfOFk}rrG}Ve@C_Nbikc`vA`!-'
        '{WAS$?0K4&W_qKJ`$Sgo9qEvll|dm18q)$AOO{hi%4Bl(^{2KT&Z<&fkHp)f>0XCoT%{ygDiavpKtc}F#V(`7{2a'
        'o5v?gA}&u@QzbvuG?lgj21sHktP=D0VM?O&_6Qyxx90jTms>ELM`IzAEZJE&9Nf~)|c{qYSQ@72qsDiI3pn7w3^@'
        'pa+HS}lLjWnR%=#Sm^iqz!JYO_bnr~kUBkLpf8aJ+nRi8vPT%GeIx|9O;Ea5=G7&_>y?WE62zMy@&24~ofsuFiLP'
        'W0rW+c=f9UAJ-'
        '1e6*)H^XQf%_1}ZBPW6igVuAQ!f>Y3LIIV;sOrrg^{)!8Hc&7+_%mQT`#iIquu>5Of;Ge+p;~~e0<*F$o`9$_C_C'
        'v8*xw}>uh8t0&*%h@y<5c967ki#1a_sUw+<3|;gSJ{V0mB_h-MZ}sZ@3P?J8&pg$L?_au@fm0`)J?Lyk>X5rascw'
        'KVOvs-'
        '+J}Op+$H&@5_FOm$`g+qNdA9;56rItTxNjVt`I_BmJ4=qYxvY^n`lWB0nt!_1EHQW9G^9{%NV9H+f?EQ?4q41f|g'
        'lk77aTXGb=&q0fkl!n>rvja{Ih96#NpsJ7w2lXvu_QNuWqMUhe-'
        '{2I7@pKoHgDVYoSN@IEC=ss%KcK+O!*z42x1F8<hY6$&jr}!8bXP!UaxLWY=3YQ*$|k`vDT|!QbQ^xj=}!u{jJMy'
        'pU?6~qdqPSC{H5_g!w*H3rX;C6DkXF$u%Hm9gjq*;Qwy(fCLlgQK<bq$k5ENlWZc$nx&mE@{NbxWzV}g6yV6t4oz'
        'qGzu8ax{aN|lTwUApoW|bK0*Z(+kJgI7sEA?*(13CRG#wG#xuy;hpETSQgaOk9rHjX%f3G=MT-'
        'w_w5ojc#~r);Z2>}9~0Fx=z8#>Q$l4z|ZSvy{6o(8WX}pDrz<_X6Oo*Fki-kg@IB0J?XtMm`MrAR^ssm=#7%2s!0'
        ';DnsVc{PZqYKBYeeF5Vvv!WX^r+nG=4lY#VlRue9I_u0(VPDA=wa9-'
        'fMVL2iRhnbEjA7VD^_0DAk7kR>R>vdJ*e?&^ETbR23WOmWWu;4FklYS0}U5mX&L)%UqgNR)evs<(=FgSkoD`v9L;'
        'xHUzv_vgx1H+6X0?C^hV=zy291Z{-@*MgIa=TJ-'
        'n<~{jKVapk<9%V`$ZG(XK#;PFIZwQWuyiP@n(038<Q}QBRuwa%#6>b_Rv#BdC!(QreA6O$=PV<4*dpy@VZd*AD7v'
        '4q&6PxUQT{m<xMhpJ$wg9wG!wSJ+y}x+kf^WeB@Ap|)qM&b16F@Nm8rn%3W2Y)1#+|mf*+(q26|nq7$4a7NC(E1b'
        'eyVz$kxht8f&elmeSrDH}^~xD~olh24KgBYf>&puDfUM)jepd2JBSSV}J_!Pg~=GyYd2y-'
        'Q4|~+nYUtrI;|qTFG}q86XBjN$wH!0~cyVpBx(aeLn#70k)-p8pgT0BVgt|*ANc+!YzOsPvJ-qJ5a}wfHlO96l=('
        '>sZ&F3`XrdIR<^}diK5JA2>_+I>`zbxLs5%1>6@Dp4DEKt!o^Lut^$+yhSa!XyG1$N*iK9osyh^F_%T3g!yX1C3o'
        '~|9>uk0y#}g?aQo7u&ek@?4Y2~&Y({~b*65P18kpdkGM0byr=tK0sZi~&&WzYOm4gq06;xAUFXaZ&8FE8Si9EU$H'
        '?lo`+XF~LA^u`{IfyK=ujRBAbMGN{YIl_O7&E2!E*p)WlkCr;WPW-EH@Y|#Pz<7pieiKKfm35%KU0ODJR%sEkVID'
        'kQv_MT$-J#f-UzfW^II&4A$ZTw|3m&^MmvK3RXY>RQ-'
        'k2O}2q=LuJJ%8?4mZ+`bUj3dZElRlf|u242ki$xDWuiyQfy2Yllp9-'
        's1FWv1wHF_;;mbqO)7V*n>(s<0O|+nS$}f5pW-'
        'WYd9QL~q^8L{u{eZB5C$i5GYRe8k>%oGV$T910!fsU5N35W5Wp_uH*Du&*CGXubyM$x$-;v0%RK*z>(;S|kw^yb-'
        'Ymz-D-Iy#)fwp0u{$4s&lgr9;iy$4mySyV(xq|5ur0)~s9J3c#dxXQv(CZ3i6xkc_V31+K>_FrEf8YJ$>KENIOCS'
        'AMtkao6c~;_{XsDv;}q|k*gJa>g<iEQl?-'
        'RSKv|v=B5=3%dV$W69+t+o{G4vvM(?}_1ItUM^0fe6@k>C8SSycc13ptT`74L92b`$^N2-'
        '7Egvn3Oi)vQAf8)Ruk?K*0tB!W`wn0wdqr;<T(P>-_EdAf)R)dX^3@A66&xBqX9<%|SEDXzGud1{%#0h6v>u^cf-'
        'F!3EB+&Xf=&kBMH71FTr_W^!Fl8%Q=5UkzIFnm&`NLct$V}XYEzs#GsE|;lPYo-'
        'e*0KV1FaM=M1u~+*+FA;ctLJMJ^ZM7<>xq<27-g^VN-'
        '{8LZO#m}>p|A?Hpg+}V?yGM`AF`L`C#IY2~5g73tS!Ylv84NVyw8YLTBSc^kl$zfVDdAPrL(i$NY0u=Dp3&<)_Yi'
        '@U8;`Tcj8Ot!pZ#GrX=9beM~?QQo{a$UP)O+@mpktR)~OKu6Pu2Z1bZ2QushieS3~<E7Wb_ffWS<Squ>V>;j-'
        'bt1`802w)e9-}J-Y0VGBdUPul$7&&RwSuzG5l}8X7|OjYZw$HB%s~dNIk-xxO+VEeFt&`H#TM>ZW`q^4KyNR=L@|'
        'q5;JZoh$T^e}V60Pn;KDbZj$7aIEy@GE8pTze$ljW4Tmtcd#FtjqH~no#BmMvrC&aJ#EY7rScFc?|dQq%{raT0eo'
        '@ravCmUJPw|BgT@Vc&qa`u5;VP9(!*zkE%9((H}80m~Vbpu&@M}&`mQ%6sRHTVV`zJU(4vlrug1R?qLwu~5ZVxlA'
        'gfIc`5dLF0BGt?+1=j(%5sJf{*vHCmv6OU~;B}6LPL2*WhJ7J^};QS%MlzSnMc4UEY6L82$A2#xsXFTpv;!b+uK2'
        'kZPO>4UdiMc4L=4R>rWv2liG@x4Bd?G{}^l8K_=U-'
        '~}L{8d*QJ0GNaS2N9ybR?rzA{L!ohvZN=^99;?!hQ$_fsyyczAx1t1y^jCXJ>YCW8x`Td@qhOF!sv0m>W`dZccUV'
        'WyKr{aiPnYDGAQP>Os8n88N1dL-'
        'p;Vb$pVhDoPtY0~|wVUR|L*}8$8&C;{MwVDe&7!)Wg#bN?g={(s52)4MF#rhVxi=>x``WImrKH-{-'
        ';D9X^2ssQ_gncLMH@ece?6|8nwvp2zwZzrOoxaL)RR@>DyFv>rnrZP#W+oot`7S59d5WZ|cJoo|)~K;{L<a0KtBt'
        'rrdPOsKuhluA^rt*!`@urhZ;Ov*BEtws_;WXlcyB|wl?m3?Pe{<8aBvv_`=v3~+beAqX{JT1`s*pUsehw*x!xc=8'
        'v`9aV)y(%IMojf_^)@W9}rbfJJk;W@=o=;FL$ipdFT4wBM$bbPQjNw*dGz)BT{tKu(YhLOa^(4BB1!w=!J?bXbOa'
        '8P@5L|+VJ#={N;C5Cfrk@?jcQK_wtH!V}+tdBX(Kl|8U0s2afeLq(PzR{vIab>jV!D?quu%DoJci_cBAFvGXsX(4'
        '||~x<W`I<$0*n=vl+C`(-Gu!SN#m?rBE-LCipm_+N(QitQZsLE=p+vHZnS)V;8?$U!&Ql;{f6e6%;6Sny%aLg#S{'
        'V^7pb6!J*?@rd7sM<3s56Ik+OkU^%q%-Z4;R5mfLX)Ys29VeG-'
        'l$+wkJ(fSrvd|TjfZl`d#$oXT=9(r1`~T=I3ycCJ_w(^fK|%D8wRO-'
        '>fK(<1mvkpM(Lv#fy=&q`?On~7#y3cBwFupc&Nt;#6&2AFm`PWl`fxY1-'
        'UwO!xAqKb4|{Cub7!_aQ<inaL1Dm3G=qDGl=@uh7C~TY3Q<TIr;4KJSJKg9X&kG4=hZe7kUdUnZL6*Tm9FwN2R(0'
        'emn?M>yX7Pxy4O$iwZklQFN(MLMXLF?yU`LqU?E<~E8=$1mEh0YZJQqo^K{9;6&U8AoE~I2bpK_Z+?nXJxll(2os'
        'rux8j<iV7;azdx=S}EWx$K%)Nr+o#>R1U;Svj6Aeo%&CeXu#D=SE|zS%=lnH~0D7SBNdg6!VmTV1KVps^^AChbjX'
        'k+jnfSUzKrGT_%>#qaPDrsVH=zu6PVr{S6bUYGdxL!CSq{P4AVEr;N-3VmH{_SG?cj;}-'
        'kmYK8G28Az5GU7;6QF!|16fOb3)QPtm7jvP-VfBj4GZB#RScS)mxHpho%mVLQ35f*D_)2aD)SgiMvsU)L0*-'
        '6_FF;3mnvU`wHk88opUo5X@s522n-'
        'NS$xdsE0H4?e0PIaP^b<);mNXAaTsLD4U&a;9OCo~wp=$QW;vf^$Y@H%qt<n>~uk8)7zBWwBq%`X{(cW$Ik6#^$Q'
        'H2Tsxj)^`>_=w{fephN3@h2SHIAN({o}2hHi_C9BkXi@k+YMNyZk&*I3q`KF$26fjV{Ejbvx+h^6e0UK&-'
        'd^Ih4uh4$}@6s#Gk3;PgKSZk%DW$C1czW@OFBEX0CPMQ`XoCflXa74;>|waAvW|aPrYT#lG-yWSKMu%ni1WU{l~A'
        '&dz;OJ_6cI4?x%(@k+w%$flkTjSQB69<e-J9`xQo4ZnX%-'
        '#&dbYbvkXK(tzb3#0j~X;8>CHnk*y9?PP3)4K#$PT;HSg+_4732nuhwr2?ADDz?9Zp4^N^y$&8vIPUlI<St>(0-'
        'nuzptNm_`$dH^wf}g6tJs&{91S@tW(lmJi9s_z}GGSbKTpFE+sgL+u!grOa7L1h2O>Rj9v?8sg1GOTsE@D9ySkxL'
        '*q4O;cLaTb*Z?TAx}7DY?Vl+EWx|i%$bK?-'
        '`XGRY%YiGUQNS0mMabW%D?Rm;>*UUdXKfzb>MC(1S$xhP%Cy3#k*W#8V|R~23H)t@bgz$a&z|r)?Dmj5V~58=E{<'
        'FJs-'
        'E)cj+A7n~bM3c>u%iGJKKsz(C1$@G+DH0l$hY2m*Wk5U}yv$>G>s1o}~VWqt><4m@O2n4EMH;b+sHG13#+n=_yF!'
        'e}le7XbMMG~6|qPWALfBdgpX4ev5n^!}EV%=OR0QKm<XdjmCxsd}Uu1VPbl${J{QqlJvPfHe~d<*|kFSFp>q`htw'
        '?#G-gx7Tff9nb}7N!hWXR*0XMa!Q>$0q4j0~k@uK!!-'
        'tQ{;etc{R<6P=rV#5ZerzOHs*Y~O#p)a%wZ*4g?aJ#&)V?8y)tfqVB)wq-'
        '{iOyP`Xy!xTrgdzrU*UdkRuR|RRm;+rV9vo8v@l<uze>@Egcp&7_BTap0Eo`yoH<h%_;uMK)ieWA=Cf?mgdfpu_('
        '$;h8tlD)x&jlb81dq;y*$%6Cm4?rh<x|P8nic2|}zbf$sQZcKXRSLNJ?wMG0|P69e~Atut;}h;P0uR|_FLpMJ74p'
        'I_C(+cbFJM(F}-'
        'RaX}&VG0$fpBgiJP9`Z^CduC<y92DX?&s<lfGEU>c`1P80G2i8Nh+=8`nVAGe<rV}_%XoBe3+?{**ptCRsJM|lm*'
        ')2_t~7@#|t(`U))Vw1VNy_xe-Aun8imz8UXda41;M)k(^Ct@fn4J@$&&7$Sr(0y2xJS$rgG3=TosqV=>R?g3nEdf'
        '%}|Vhq~H2WD^P1s)Q#ExEMEy{IK-jGLe(W7@x~xlY?G?q6z4&nLr2;^jR4#F5>>zI>{3fXe2AskkRoAQbifCO0%z'
        '@mNUu$liOVUeh2@+=*ryfvhH9EQ8$ok=8^9|Pd3S|S`UI5f1EiQMZ_Qadt4yVWAnU6p1@W%343i?tkmFmh~a~*@N'
        ';?RJ-!oqb7v?synw+6HkKHkJr^{bP-mQqPCQ#YzfL6Si<{&np7%u$24R4G1EYLID3zawJ%Fj(o8<($hG+muIGq#C'
        'Y{ZD|WhQ2B(0G@NX%}<<H@Oey4tZc*$m_eoZfN3Qdy27)J=zs~FBkt8Wd88GclNEOmGf+0u)54%y3+T>@X1^ik8>'
        'zXm|D4OOpFJ0;4wV^mv<l1PhA`)TsUQ}5^X7cJI$BQ<mpi7iP2?pj(@*`Ki#*Z2H(txwX!}(`<mSovhUJ&O}(xLl'
        'X2N@wYc!w&oZM{+UojbAA(f}Dj!Qc_#`+iSXK7cBQN3?6<Lu9M$<M8Ksa%W(vvN*Zm5Xi;MB!Z63S&kpp}td7oEK'
        '*oL^r2&w2j+i_7!NiD(cQn!I2qfgN|MdyGoZ#>MHNomKiqK_uNdfsJPx+p5e(6Ha7SWR9Y{W7+CV=i}gQeGc1xrw'
        '57#wz~-'
        '?MKa2KBIQWCNF4dDI8=LA^%4lOoFgy4&D`5tSmxy4(5)49xr1G<M{l8|XH;q#_FM7ga7J&9OXgSwS!Pba84Fpw;k'
        '}9s*{$a;JzmP*FxoV2DSb*Y;G_zNO9}$dBE_KToJ8I?3PaAqN==5nfKT~*C8x-'
        'G9}VZM2oH}Y45Cb8QwI6BprX8@TyO%LrQBMLs0QacN%{E*k`%O<;cT0mcD8Hf^TBtsCEkswx(<&hZFyII1Yz8Z;+'
        'x`dC}`m|uq)u)^;oKir^+9$v_w3%4QRtdj(bKEGbmA6Y>KYjHT!KU#Il3v)ToY~zY>#s`LD{*Q`MTVdlejdAHt5k'
        'sB1%j12x6n7czS0y%VBVDO;VF0t4W_RYl(>-z-MMuMO}dCV#zS=&yxf{KmT{z?r~kf_LxVe*fzHb^h+{AJ5-'
        'k4o{aE6O+OC1GL}mqUtt)UzsYQ#{0^q&tq^_9!4loqBADB=bbKZ*i?F!m|UFVzvKmNEpUH??`yKHrQfN~k8U5uPL'
        'KiM8$j#}mA&k9V9T}>olr<)n=}EE2glInYTxF*Uxa>|LO(}D@fq`$Q3zBD>(Da`l|D_ir@?g|8~J@IFQ)b!D#zax'
        'Qpmo^p1*?)Qqc+lzAx^QAZnZyBW}mQ-'
        'l~r|OM`XQYLUiK>ia4Kd$4d?D`$)nU~oIDH*S<8Sl%@OPOD%01Jq?gQB%f=dNA7F<nY&)NqeXNAS(<{gxo}Rc0Ku'
        'vL4%l(5m#4r^WWktUShb3IF?|GfenfhMF9hfXs{{=o%)F@*(CGxNpNzv!pv!8s1bG?F^}4SuPh>irg)?Di`o>eAu'
        'keCpNDt)V+)e>z$H`=nlGwQ9`Oge&93R?i+3-'
        '+zj$@=;o^Mk`V~Wifb!la39p^ACpbKav%?vH@2F6o4(2PvHu5{(?j?>G`O$r*C<{O86J4&x?o@yUW_TJ58-'
        'yP1!NK>-t#L`YDfEIoW2^96;Qo{B<9Y9#77xy(nod-'
        'H^9{&<_(AXr<RNg<nGYM){vy$tYMo{S5=$SxYJtTXMstR<L(R$Qoo1}rc#<bPc1gIWM6@(m$qMWup}*_`odzxtDx'
        'Zn(`r%F$5h6)H%;=HTKy!U;HRB&t^Jcf}N}bJ_8vLq2Tk`TX-AEU*F6lyknEjGBRh0WmIjC@hBxtU(waPKD&#A?j'
        '8CY0d7MbeVgjq}E7=vyuIiaqXOCdG=-'
        'ans^ft&q;EQ@+u9Ylf>O$13TN&_4?kQw%|r)wGcDw~SG#i6)5Z=Qr#aCQuuK;LJ85#FmopI4$FOJqma?-3)4-'
        '2*K>gg~V!_>$^miDOK*%+k+Kzr+zGIlr*2X{Zf>=^s+D2lfak!$Sn7f4+lL=&mT+fUG9_ah93s9@F_g3Xfprn9x;'
        'OgK6$$I$wTP;Q^tj>IP?uKHVU;k19ZCFoSXUIcEC=vlHzz?fGR9JEO0|j49@!fGTn?XxBCe-UD~pV;rA5%*=D$o0'
        '7*<ThAF<q9$^Be9gKc1>($4Fu|nCZWK*SN4qU8htyig%sl^;*XY}c$~oGbFNPyz@d7x5bUAZ!`iGh!g~C@g0%Y>q'
        'Pok6GYAT`P{e=`(z-wq8leAvfIdQShsZa4?n!G2_z0Hhq_3^_P-FOQII8KZ?=?NE%j0tyQ+?A-'
        'FlU6ykCixksjFn>*cI#50v&VRFjfZByQ9I<MjUX9!(Yl+D;A2VS(YJO(LQbm#p%+Xy+aH!j_8U%`3yc{Gu7((}QG'
        'Q?EY0aQ7Rth*Oi|xGyioSOnizzSQE25ZK3%esF@t8wfGP}d%TiD0EBE?!-'
        '6wP}=gXwwQRA0_DV{`s{{`$q64;L>drOlo6rmB6Z$d6zRT#Sz3MZ-'
        '?sy?Xn>O};wvID`#knT9g=B*$n9|Bhrlc7i*{5*?G>wsvdlCxF}Pm@?%jE5LG?eLFJ`QHbB)+250sAEV|Fo=IZ&q'
        '4k8atU2|`e|~uVD(Q=xZh&m=-'
        'R~IL`~cD4E@L#s+fPd?$04`HgF~<pu{!raciQ)SU(F+tWevM;e9X)^yE{G<1z3#5`hWRO=22r|;p5SP1wwC!qsbG'
        'Pjgn`BADu??@`5zeMe|>epo$B{o?V@b$WF2azMhdiI+M6apCBOxo&AGTr!H~ZG!y#m-'
        'Qn58BhrzVBFt8C!dns9Q)Y`V3Axq=k~-'
        'Q@>%Y<rXwuUx1Y>k}E*r62Z&$ASTsF>_i&~RKUKd)2FOkr&K6#NuHXFV`!j0^~#V_VzIda<~@T5iL3dG}B#2o&T('
        '?`k&{ERZpk3-9xokfN;RwPDjoMJ4tkpwS#d0UjPHUMAo#M%D=POUhQ'
    ),
    '_portable_underwriter_0e3c6ff3ba97.reporting.movement': (
        'c-qYx+iv5y_1#~=HBdmxDxM_3JghNZbb$7;MNt%eF${sRX-'
        '61|(o#~!+G+lM&*7aE?Qyy&w!vU5ljnZpIh2>n<v&FAO83)!Pmhey(@C%s9T?fSO-'
        'Du5x4b9qku>dr)ua>bQ0<4R<*@L|8pem!a=BbAj-qWySsuq>6s#;s)pV^G2<5yTD8l!Pg<fmu@S@=NZCx`-'
        'tzXgSy+QgL?YfGe6ihWRF|=*no869yW;8S<$S@(e+5gNZ%ZiUpHxb$s-'
        'Ypi313Qv(s91@bmS0(QdKuWEe6Dz(EeQO*(t2e58lYGFK!u=FA=ee?eEm*+a7kiKDn1m8oZSEH0j?zknCNrgS0_$'
        'DHPN1{1}$tPAis>14^_<w(ji}~;iVl1(sy+=45%3cfLco@&5bliUi~t%0=T|1(KE6^u4*w;pal^O+`&r?viX-'
        '7S?(cg8z@xZy>CZ8WE#5A^7R|_S&*jUHRGq@Wdk3XB9SY4O?Bv6&|i_-k4--|S-'
        '=GBLLOEh$z8}>VpC}wFoeWD)@>^?WmEvSq(6k1D`b)9E82tq8Av_k31a)Y>N2xbkcUEh3#55e@MRI9Xd61Di&j({'
        '7JaKBb|%*9_EgsFmDMW765$0Q<cE(8o?+~2w)KJB^G?MR5Iz}k;aOA8_1;$|U<=GhhfG1Pz;&5+)!223eR?+g)lp'
        '{Xs_OT3+p|p4D-;@->bWn6w%$Cl`^TqTN#nTQZ_vkfQL*~bEwaOj^;&Guxug4-'
        'zV^<K#yj$xMCch6`<EWlnjJDpX#2Rnf7}(?8U^XA1KTVG2FFri@1Z^k!;zi4Od}#5@Gw+%IRw|!>LKtda`uC(Fw~'
        '59Z2>Xq``;B2s0YvVxq@7u*2*cmh{$JU;Z_`^&j6Q-'
        '6WYM0_?L<wHp_mX&o$FpOK6ZwfdHC%*vj=?0AdS(dhkKIwy$K7h26|0b%^P*I$r+}t*CVM4XgqXD1&vG=rYd`h2v'
        'gC>Ohpn_TRTcuv(r7$^|t$CJZgo_D}i6*`NG}{JrH&xnY2_thT8Wlp)KvY#8Mc4EeL%0-'
        'Hz*xfACCwA>59C2cr@2MXYl+P&lF5i}r*#J$JHk$Hu4o$@`KGsZlFa2Al3mS3Kd`xX+OKoN}t<1LgVI<y$ovfT8)'
        'Kv0L$-'
        '9^08^~s|J^?mga)~JtOjnZ+4{+!35mEY6cN)YM*pB_^ikG6Fx_pGjUOL5l4J&wBR!n$Bb2zF3*zU3OS+l!0CDdAW'
        'fAXN^j+N2wqb16Fj-N`61;}y`lYQ{$DSoYPg%<p^D(N$Odu*EiU+YbU86wD%N<sDRO^|03U8Hh-kAPmmt#MexrKr'
        '1Wxprh<Dw4e@F*{=QCN4<<=;I}W1R_<sgdm$hHayt~$vra5c#qep`c=U+dwU7x0prPepQjFDZ9y|T_^LNDFApovY'
        'evmO2G*y-a9w==+HoSzRYyTw+ES-$nJa+=nbJcGie3lw+<Vg=2S+;8^5xZ-ylLm9KaH-Pc1hFR90v(XI>LBf*wSl'
        '&w_m5ksQ*!SJ1<+~^1XTY^2j22unP@W%>7au3ZT;#KQUZDbytU+Z`5X_8fH?x9X3k_u9H_Gq+NVVFTky1|(ECL)2'
        'MGHX8Ye!oxu7=et&UMr`7%R6zQo0@yO?rTi}K_~lIZ&t%yEn#vOt?}!8bYgotLsay67e!KA4)7W0zaZai$s0pT38'
        'JVWP3{(N`n^9i<myhMrE~C>!{Yx(r?dE&CVf0p<wi5WS4=9PMr!d^(AWm{Ki`oGND)+o6;K+sQPd9~u{Ad9&Ywju'
        '#`RNMuQ964Osej{8ARko3%SOCh_9>&53C$Fba1--0hYdvoy@CaPCPq!{;DdA-q~<@H45B}{kW772y5cNU-'
        'ykSfoRf_jkqW+HtHxdLft3L@4*iTjrOm{SsSx`uf!8`=TdH#t9Gk{s9>^GIUIZ-ttW5R>t-'
        'Vc>k2|Fx|7o9={u7nupj=+^h>%u}K{GyHE&q;p&Z>IE}RO3#4CJLy=@PqX%R8<pfHn+3W%G`1$Of$p8Z?ga6U1dA'
        'V=dIkZ9hjkCC2jn+;4h>*K+8?C2Y3XJ>uki@UBC7R_GN|3(EnLgA#{+fy?d}dq7OHs5=-'
        'Gxr3W*|%^c3x381CNYlJ5K(;I&_hr`OelVFA2~3)Qf&nUr5fpAbD=5H0?cn<h#ZosL!l{+qxD`gHq4Cz9Z5^}FMT'
        'D{`N?xhiw^6O?}e2Vc4YcBPz{4qtKKsE=81{T+JVNpp=LQYp{2b(KeWAhN!j!&2iArT`%lDv2Q@u~5(M1VZ_fbL-'
        'r6MHsk_T`@;U!NxO2lAa3*x2=t{@h#<cCx3T}cW2?UnXUL!gwt4_b_H<<eCh5I<9l5%a;`^=A?ht%rs~H}f~<nnU'
        'R7V-'
        '?N%jE$`8@b|JJcet+`9%^>;cmu#im9nKSiz+8>Gj%Ok1Vl4ocHN3`(^<tP0T1{SlZT{OeYJ$W?O%r{P&`q*%@#S$'
        'YOPM>hvSf0z8KC>E|c`SjM>_~FgoZx9BP{!=B2#XHhweQ0IbveD8+H{4QG#ED1t`LO)vzFLR4`ID>cyI1;DczDXi'
        '8}0I=YsoVr9=36SX|J{kF;AAi&HkO83aN@#WdH=o;6rCyt&1@3kRetcjW$`ev4%7lNcH`h%-'
        'q7CN<GTV9N$1rM$Fx(=mazr6-'
        'd@fz;uf75^_vyxWAqzlYVw>k@W9J^Z2K{d8SCKa4c>68=3tbbB1n{W7wRtJBYT@$|U!%ZqEhFHhwmPkirxK$cIkJ'
        'X@X@RNT%AqH3J(qxK?4>7I7pYobdtLRwIrHE+6+^-'
        '{w8P$6t<9RReK`WFYPcl6%2{y(&`sV8i2y$SuF>WqMjA|`+mY>&Sx(7)J#h8}+b;YM;}4}h-'
        '@Xn#AN!$if~fmA&RI^Y`@{T9AZ@20W%&$pi2ww8PP)$J$p<jthC>KXYrmes!s(TZ%Tp_;KD$TK69BW-qK0)J#e2d'
        'Ik_cAl2@Wsi4f9LhF7{E7V$fO^OI9cU@J4?cqdWmF5DUsGw0X0_8-'
        'C9lkAxiqJGe36T3(#xpH%(QU8ch4J{T@jXfW#S>F@5~qRO|EV*_@QdZ4;%7`YKLT3kmeo3%@|2;Tr-'
        '4LhVnx?H>_P6I_zKYmo2Xls;%gqx6#M=O1M9QQ3sYqGUO{-'
        '*O>}8(49{)0Qn>@*Yg|1l)~T*G=*kHv2*Uyoj_>!wU>fkmB3q}H+!AWX~WFD4Yo;Mp;-Zorq4X#yx&s=-'
        'ZXFbXCa`?<nV5GSJD<o@6MBaL(zW_Z^|;#N4oYc1Lm=h9ErJmJn}QoyjP-'
        '|eC7LVi|FVcN7DFntcUeYMHZclWS|3kv;LLsuV&&r?+!E-16~doB>%^2HgpT}6u#pD;kF^M-'
        '8LeIawRTnW)_IZ6ltiKcp5C(9E8Oq+zZCmaO>t-Zgz>T?6dd{j(_)V'
    ),
    '_portable_underwriter_0e3c6ff3ba97.reporting._underwriter_html': (
        'c-rl~+jbjCk|6l5uZWDw$^t3@2&6=%M2S-CmYM3JE-R_BDx1Xv27v$>DG-5<07xR)IH#ZX?7q&-IsFB@A22WT-'
        't)d6QD3rV<~Q?81On8hvuC$2DI(n6+}zyU+}zyEJdWdc>15m;=F@qSP18~I<NKHUQF)q9Ceb)AqWNhWEvBQixG1u'
        'DT0})U%Zqt0j^i6Q#zlS>4F==Id{Lx>L6n_gS(Hqt`8=6t`Lw)oLw-A*pH0-'
        '?zm)k@v>oP?NjjvOz2tbP0K80Qvut`I>WmlD;XKbLr7E2ii@`7%o~ELFzQnq!@bPph@#+m2+JkbwoTM7W+vjgyzk'
        'NS=^7!5J!P9r|Zrr%>4;pIgEV(SRU(>y<_Ki_Gjs~+yKA$WHzm%<Z)O{G0^J4c#1pfmhc$>n=r$nP{TFw&~%_w?9'
        '^`l}joo8ohl$OI}2A`3b*>nOlj?%N^bTk62iHrz~Fcuy4^6{8zNnB6TxkTX?ASYHXM6bM{)$YN>Op;;RiXYr8heb'
        'A<$DJsC@VCFIUu_sAj;BbGEEaKaa$2)wImwgJuA=?{477vvJoJYB9Py8mlanGnN#?2KiD;C}6PWyw{N2qjke`6QF'
        'zzUa5fN*R^5NnvozC^x)9ElDLB%~{jNWK*HY*i29Vji4xsr02WqaQzlQQi@WjafWWS$r0UMue4ICtZA+X2?1-'
        '|U;A&^OrRZ+~0#``dTowywuWs4LtW1}i)?71CgZzb&@=+jnIx`m?guJyYwRtR?<C&*qa9MuOAR6KvFiX;8E|h|kh'
        '_f<%uG4`QkuAGSNuKQHomy7#_Vq;1YFh8}}wub=+;<?~nX4I+bqToUhJyx)I57ywEHFod+OtCkN{cfN%izS)2Me*'
        'fpeKZ+)NWz}}{=JC(_uOC07MshM0oo?LFqX9}4z*7&t0uBSAkP_V<-gtojM3ZECvKOb*7(b-'
        'R=pnR!fb@%or%6$!^SyX6A9wG@reK<!rF-'
        '#tmR=w?#}SH1;M=|UA{)(5_eSY?HcY$pqXQhC&9h|Eg;|<_=n!Ctgb!WXKDa5qV+|5Z4{roWilsMYv8jlIzWK-Kt'
        'yo~?EFEU!YzU}<tSB=Sq_EJUc|MEsF^MH>Db9-'
        'Q3@V+cWiR^U%^Ql^1d0Uym7Il>A{%w*=^0GKJnbe$nv}ayJWr0xIEsl5mp~ArO?*GtrpPa#NwS#d;y-8E6y$2F--'
        '))yMO(C4Sr|yLHV)YJZX}CTPXMcXnr0`b^WErne|D+9&k_=<yU}@4w7NhY;G*tUJL+2>wu8NkwWj(8RK>*ZVrQ+}'
        '*h?q6b@%+Dtvbuk(_%cyFLtBTY&1%z>N{*{d7)51taXbqjG~J>%WkxF%V15PFXV9U^!w^Nw(Xi;V0yAynU$*e;uJ'
        ');7}9Pu%`b{%#>e$LHLtJ{FG@2oAe|i8_BJEkSyG%p(Ig$u#jFK~bGDen%CitmCfUh!H!2YQ5M7Z)%Fvu*!F?aAe'
        'rS^W4rFXgkTu{@Rs!EGkrLB%L$Fb#K5X^-zpv`5mke>`L|3LS9L;@ayt8DQPJ-'
        '>$EtA?6Lf|g);)CGfPYf8<tK+2bsX3mcmrbd8>n`JIXxBxS+>H!lMiDVf7x?xJa2tXwO$#kOu<jjiEq9Oe`8+?{j'
        'WqBu=9A<&o%r|*eXGldu>lTMOF4`}nW8ES{J{vdwS#M{qCpQT!3qvFyT_Ux2>EizIS;u!`bsE>$#h=PL-'
        '(Y}7qdoG2~F<DPNKwVo}Zjd((dsBCUSa^6j{=p6=_+fqrG?zN=kgFF+9!-P)fTN-'
        'H#`r$EXgDli>#()O5s)yJbE$Vz#Pv#aar9#(HUCum9lc0~{7-'
        '({k5Yd+O({ZQ4%+ig0j%Z5)(Y(R;gXQFDt4X^Zlp2&VJlX=rSyR!I~-%jkq`QDeD7W1-'
        '>kjf1eSShc8fxhlt6@p6YzqEcX^A_Oc3=ZIh@jR)6Ia8e%{x>~&&sSu)-'
        'qY6QWW7qjfCs@$?rR)m*nf~#Ics$96AMSq=)YQs^%CpO;%qQ7MtuOlCwySlEWRxvRwFbqn?%Akj8N(TG42v;HWW7'
        'N27(=Ls^|2~Qy%J<E?bWnngKYKM*R)-'
        'nfxfitjte*;NXc#15rahQK`CUTd~pnNaFUJZe)o0!8C<3)oPhxFzt*DLSO;H2IK;LKdOsju4vTz)^=dvEUD{$b_*'
        '_4ad|;w;+S6bkK~5|Qt2M}K?H)hcd+c|2_}09x>HJg=TphF!g>3j?sZjhCSY$+#q7~$P#^_MV^ziR79<>{DES|$)'
        'FiJ%#<VncaG^Y8SpJ`CV2ZZ2%?^Y-|wt~+OEL)}pDGz$;dbfkeDIz7R4YdrTCcArSPxmJfH|1G-'
        '4Px#LcN$h48G&Da23rrR*qtOL?A52)WJG|~kd)fnzi;hqL)Fq@Y+K6X(vrrCfPTjpo4^btPQGx?eZjeJfQlw#ZKa'
        'W6-`!{jCi#wG-rt$ESR;No=ZGSYr<PSBM6&$v?hfzm+#A;|#&v>+mrL@RE}IOeser15vb)>8NRK~c^RC9m(@C}i%'
        'G0(zubcMKofja|9OZq}HTxaYF*Xs9n<IO=I6Dprqg!`;HD}uyLj`j*8;j(#kH>!Z6nPtk1c$x@jB+Q@jB*Bb(7Y}'
        'c#a?-u%u-n4&~TREHU=A5hKIIpdJfe}X);l3Tb(Iku+VS0Msr3Te<xsogT09FGCpijO*T==-'
        'SZU4FgkSL@mim%?wNzg?Ypza2Yxnd{ubq9J|&%RjS;Y7=lnR69>>C7dPa{jeN~}$y=A(6&1K4Q9%oE`hg84t>An)'
        ')c><*x;O2TvBm3nz&vC6-'
        'nv`a96cfbi*HxxuUu9ZkY1yS)Kh+6R%Qk1ii9i34YV&RHmQ#Suhse=H!a(6KIqH9`)b5_-'
        'g42KKbmn5R)!V5AhepapGEuNCsKTNqfjJ)o$N3BoX|Oi3If#mWZ|jz6YDqBQbx_ckWM+1n+^%SnUV>7;C{Pn3Gop'
        'p2oJMZ~RpYaCUSz{A3M~BtrA@72b{hngl3T(UgnC2U(;h0JEABVyj<D1v)8)l!TBK{y>yFaNJaJC1Tl^4_%x2w0T'
        '+Zv|Abxjkb1OUHZ8s4?4OhwbrxTng^d;)EBAaTnkaKS!>;J=9I?9r$Wu07ae}`L*8gjsl*vtf|`Usjg!svLHRGi>'
        'D+vgXmqL00r*E`#N2YY_$r-iYwS2*U3Rn?H4YZ2aThwH8uT10-'
        '0$Un@I6KpGH{PAtPrXA5m_kDd{y?1tIkifg#4s1@NrG}w(T(0a#_L%fn!$ap;nW4_jtmv}VN^gPKi;?y~3rq1DkH'
        '`KL+4jaNb6n6MXDuWy`0c?2Fs`t?G#jo_3HtogB@87QVN;HZ9xe(8P!K!(w-'
        'go~ha~d$w&U=TzI0l9tpQpsU%}Go+Mt=W@IjeQ(`k6+uWwx;HfUDEt?dg?ml5ix##?mwpIuNwS_kOwA+f>5bJ*@w'
        't<O%Qg<E|g!kAZD6Uv&^;vvT17?W86M-'
        'lAyzTXF0G=uCJUMhUoy4OED3oi?0^D>{<a<;iW`;|Ux1I(o<r<<@*RtQ%$BnQfN)*e)i58dN*oEIR*aP)3jGA7$W'
        's0ieLHiBl!c@F!BT?2o0ZRpA5B3YKfDzcNB8dhI*GYIF-bT5{M?)b1%S!JA^fZ`PM*={l|mklP*RUbBBzP%V5lY0'
        'us%%NnJFbz>XT(^?>d*W}h?uk7v%n(g*sIRIeh3UPE4o+#o`sAx+o1Kl-Jp$T<?e8_G<|z7QQO>jRQW+U{BOz9f)'
        'A>c3vUMSDFz;}<($U1b)@Nr<Rkr4YTB}D|n&dsxNj0^)XGt~<$v%Ef9=2jT)H+Ve6pvdj9r{hspaaVEgdtL;Mc26'
        '+*@|?Z6M2m)U879bQm+)Uk>TAGyIU4JTFy{A{cEE|9(-'
        '59R>At>oL{wM`V~v2U%6yx%Sg>Jy!oP$D}*kOY~@v5_)yWEz{;V5&$(>s<iEM`Z&E$r3eefGRbb26LA&631$phJR'
        '0XHWz}C1RIQGsUDh)gmZr_39ar+bCwT`6J(OQC4)pGS%&#l2Ja=aRXbzt2J2Nw~sP*hZcF4opTncszq{$Uce&ETl'
        'H;qoImZCy9+^>`g^&+<_!?zQA-'
        'n;mal`$MPFFyXi>)K%oJ5vpFD>w|_>ebv|G_{*r}4)|JU|7zcpCMOo|A^^voVXzW_PV2_BmP42(vX&96wQO@9s;~'
        '{%hJawDd67&@P?XPV>JZJd37KN+j1dG&Qm+D7^(6I-Gac$BXvx)^HFw6@fXN&A?Nr-'
        '&oc?{XqjqLgNsV63^?A*b3A+V+0$!?i6sS}+n+!#}3#@e*Xgp{Jac$KRw^2Cm2thJ9t}oj=mHKIMmP}kq%q351UJ'
        '<xS4Vs*F4TH`L@5~rHy*EGKH*#|FWLGn7PFyUMT{yjDGqO+{C6?Qe`EA5i^;T&Nf7a>?xi!@vDJzdb&P?9gaj7M)'
        '=$X<aw>IW@rS<UjjWl-~DB4-NL2JFO0*I0gz2eFNW;IRbt=k>v@}cb<Nq79!+6;%9b#qOCuyCd*uI=N;#!%$p*_-'
        'zb00p^Ai10fVtaY!Bvpj;p@`pumydb->x~-I_LgnnQcOT=<v91De!F=fzv-ML6g4eO2G|(egJWlPwO%Yo60IyCcY'
        ';BaCN5e@{mU}VY5QrlOzbc7EOxpu#{a|%Lqm_j|91)2ogb>OuplBRXXaU_!?!_-'
        'bCB}{@NQg}E8Wunku?P;pNEpOp3@8S$q7Lgsb|B(4bnrqXgd(a0%;@;=wfyVBO#x?J=goT^V+gF>t?`M7aZ4dL)V'
        ';X76+e8R&!RDi0+7<>7ePhZ_hAP~OBb29tnACs#oXU`$h=@>Uj!Mx>Rn{s6zM4Yg18J9#koH}`+1R0e~oU!-'
        'jIDMq8Q2JV)KlOA}n%Id2kcNL6vAw^Ud(4y+u|D_%R@7CZldXoh-eWb`WjQ*r!1T;~`Dx@lZ^t1fPM7?J82(gyG`'
        'p4c&r^E@BaB?R+#{;sDN1R0k@w3p<KQvOURxVq}fH4gV+m5dvJwC=LstksBc3|ME_B@26X*TifS%;)f4z;^&9FaO'
        '>`mw|}~Kx^?IL-f4GRSE&THbsJ%Q_v4*k1K_s4i?+5-d;P5t9H8>~2_tg#e2X0>Egp(Y2z>J8H8buTk$v;5m=b0-'
        'b7w+CQmY7Kv*8fW;4E|3i`d~J@$sR}B&O-'
        'C$bp5=(7k&WyJ*tK>ZbVx2EuLL5RHY`X@@qX$+cQqfyQ<<IdR@p@vCu0a(RWIE157~9$c&UY3y9@xJK?!B_(F)u%'
        'gx%fEeeKERRg9>U+be@-~#0NSuSf8AJPH7i?@Vb0*c~m(%TsK44e_+wLlS_!m+*(-'
        'A0a$;mXw(3Dc=Zz&hE*(8I)a+nvGECsow7rlp~A?7S8qEQOlAsiOc5)QH{w2=)HI9jApRz@f3bOFU6BJ;(Zk_%*K'
        'X%CjNy^gIRxIcX=keSdUf~sU4DuJ`SB05LfjL?;hkP)$W2Zs=w3HB9VU0Hd0>!DC3C0L;SEvJe<Dm+2pc6vdCJ<m'
        '`xqr51mFh}rBSO?(bFp7T2rWweiG&)W(x}X=mJ}zM(P;xVx39SJBo~9tvwj$UavmxwFWi(Sv(Ve8{fE~<Yc3e=(o'
        't`)1AdV&`MbJ;tn!d*YvfY#vs+ug{Ul!EQQ{bF&1{@?!(<R$rIiup<+lzjJQH-'
        '#t%ohca4A)sFI?X2|<hfB=W+ziP($aj)7R4+t1zC?5C30?wy#TL3KX6DEH}{}ad_aa5`+cvDLD>i!Nu+>JjUXjg$'
        'Ja|GuA*0p4DK*xFBjUzB#%CjvE()qT_Ttk>MZD-'
        'gf;yIe+WR<LSbr?y%o?^c{(1aXpO+RbJZliKX6PyvgD)Yn@m`QI6&#d8auR-AB7t9@Eyv(rQ{r_0N;SU<~gjR*#b'
        '=`Y6c<$x7VO+d7ySX*Gv&tFBUgYJFpd5uJdGQi>fSe!7ZtRvpl_tT?YD>vbNae<*`Q%`dTG-uP@qd2C5hC-iHJYq'
        'FOuG#(vlOZ!3jBxvu62Q>AW(6juf2C|Ja2N%y5|Ruj&?;IJuYM~Fh1ePFYS!`6<l!JyHM+BYN42v9|Fcu4FJZ<Fb'
        'VQui34AU`3^Lx>8axm;v$kVuo^saVB-C^fNq(Th21DAP0}y=9mz%4C9@EX>`oAmbSP9u+|7eCjOmnTIDIk`?D|-'
        'A{O&S+#G5c=9GO<>%gpY*Wnojfk6PuDubx2QAXthcp&T#pT!Ci5zIKt&bXRA{7wQ(YQH)s(qHhyY4>AObQIzFpJH'
        'ZpJh-9nicGXDi5FL)3My-'
        '$Od+vOakVdiv5jKsPWdyR9f<>5XynsYhf`apb3JGI}&t?l2I~4k1N=P%hUWqsS~{hXno#om#>@aZM+pLscJYV<8c'
        '1aAVpHKmf&l|@W<`uoXDSPH|GoH%k1WQI+nGYxi#<C-'
        'p*NPzk%Hxq_Nq>YudX)Wt5e;pN$?qmt*(>x`4|aLP2;%;Q~^0M0}2fN+7KisrI_<;3-'
        'f_zwR*}5Apw1gdY}S*fRySB_%Zn5tbG|?7xiQxD8XWkyhYgZ8+?=qzl+LA?tMkemn9h52Y-'
        'i=DNG3_`(pZ>;WxW*Y4maq-YgnVcu)Hsavs2pL<uwNlNEQHYv3PMnZRI+3-VJc-'
        '$cDN4iw*F*eUihJUz^RpC^iephb?tVa;?(?wjjo~+tF&$$$J1QoKb7(*f@@F*Q8i^&{dyc4shK7@$1A?yUVPze_P'
        '{sa*5T0MUFEG^dp4TzH(Lgq8M*uxX9iW>?k$x;;t9tM2_t-'
        'R8{!oXci0c8M!3TWghpi*e_meq==wVXe%0f?b<Jx#Pij&G(kMpaRiYi&br&}Kt*aszZ&Smq|!h-'
        'RP7V8yq&FQen~{jk<z#aZgwO74rm3j2@Ka=)~W%BNQ-shewz9L8@`WwiZO8r-'
        'gGAC`zWy^i|m>}kMvCuqbgeZ(ZbwrhpP!?}eG`LG0CzG!gR7?lZf&x0MB^%~xxYqop=OL^+W>Pk`m4k~fptXI-bI'
        '1UGB!(9tu{^~XWOLd@2L64vLZID%6`q0prO5bwUOeM7tw~7P0m2%mvXsGV#A3mN;#9m*ev~I4rHd9_}Si!1Vtxz_'
        'HP@_NwHOA&zV}P`EYGbvI8d4vFbvIf0MKV1}E0@0H{YcdEFlsCXs6A*TfJBkNR6P}cMECCgzEV%Go;nF_yuexieu'
        '3%@eyNZr0s2&5$zB-$4=$)YJNEVDisgk&vLt*|6zAZ#={PM&>*fb&4Wm%Sn;*_~7f-bVceoGZ;C-'
        '!5>iJOj;_p5$Wl?DF*?ji_?)V_?$fC3CMEG}HgY5(`I{0y4(`X_O^dHZC#;aopns}v8zy|I?&N-'
        '@nccV@9V@_HY<ZGR@8mK=T9&^I+y0-'
        'Q#3MT1EIvvTQiBBm}tWO}dha{`v=Q<zR8_SnDAhG$WJ0Dr7UHg2*mBrt{0V$}ve#T4v$C2KRen=K&nSt2&)3fK%q'
        'D)KMA5nX5i3Yvse_JHec{U+e01QY==EAx!%RlzQ-kRP|dhTKdB0D0d-'
        'g@<T4pKNN=h6HkR}O#3G(v49&%h%6=S2o3+)#C99UyueOHwzgD72k#EJQWXj}@Tip!AupIqe*|pFzUu4!)3dvk#Q'
        'D63%evb)}ouasJ~a+e`Nd{TZcNfI-piNUJ^|&6d7E`}4F+#!4-'
        'MxymotvuqfinVl`pXr1S0!aA)SSJ8Kt9!!LP@tsCkr`Nce)YJXjv@)qkr1kbC8J&cexfGui$)+D|UaGTue1z3wz0'
        'HFLP;cz8OdY)bCN_>uEgb*Z?HkRk8=RW;W{vQ23EYU)ovj1MNP~eb%%9?Sn$&9>FR?M4_-'
        'M(fz`l*GmI4SZw)o)>;h4bCsP)C57@&O9tJ>$AWMWRi5fPksJ~X)~{4DovLZVzxeR0Lpf6Td0P<)dEpJ?&9^dQON'
        'Uq%V?c8EGPNY3@g9Px(un(8$9?HuwLLSI55V)Py^&K4rEt0X<1-trmc5=m)MM<fO)QG{&AmVHOIA`t-Jpr{v-'
        '7%U0Aj*^;ZX*an@FugfyQM0rlH&dESaw8Sz%VdthMwHV;b&Fo&B~(d@8E9Al6SS)Iaz>%a6ekDrqX4AGc-'
        '(@Sq&PQNifQ@Lhfc8wetQn$R`B(D1&jq`U)v?@Eiz{`U7V%#e79x0rSucJ=-Q53q6=7zIjx0IC#>)q-'
        'F!;*@g1=2^^`{%NORqhRsa80$B$JV88JVX=BO@G(5uyFU~_}=@PWV}qURvgkYB-nAKVlrZVmAu2h2YGYid=pe3hB'
        'Y%Nq0PEL~&r*5aw3j8fEVg3ssm%i=v<OIZwy(l4kd66%|%iGr%1NlO&#>B}gI&lpqHUIcLNzP6IcI{S~;5T9g5Py'
        'JH9Qi5-QFQv}-1l2se))ZE-{6Yq>8<pTD-@AK}5L2WD3Zr*H0q`g;hRI||(Yqt`<cA%sC5&#-'
        '|NJ*0?Aid#d~V<8*<DaeC?gmn^3ePgL&>3P*^5Z#ViY29`}8C&RR$~(qrSNTt|H%9)sE3jv5dS_eylU8dYW`PeR~'
        'PKqXq<K6kyQkb7-'
        'nonMn&$p*_x(oYFs}dMbZDd>|6N;jShBARS7oQl=woJC}w~dPL9e#x8Sv^CGVvsEm6i4UkMCz9^;{#yIMneBtzFe'
        '%AL8kh)Ypd}QHN_ErKUkrt0jFP6Z@P%)e`sWRESCG_kfH(QLw78SrTWxE9uKREehRQ4bGC3Cj>kYvHeL?y%+0y3F'
        'J#hBdM)DZ}>V?fZxTEG#kuQ-'
        'E#;gNkde>fPt*?;|h|L4I!z8egnsrYItNI{<9t?7`?_cwnb*A|w42N8(@(%a{6UcY@mc=Pz@{nwA51;OE;tyVkQd'
        'nof9#&}%Eof-'
        '~5B3&V6(ukfte*ZYyi~jN5>sLKG9=Aq09QE<a@g$u;pU|RtvV1XWSy;4tXx)1%bg(uD`05>ii%;kC+3wAo7Z(@3i'
        '(9?CIJvpq@AokWl-2vw*ZZ&EVuOSDcl~>J?v0YT6UDz9ZEfG)9@C#&$#>&h-'
        '_f6Uw|Dv@@%4CoC+Tm~pZ%Skev;Ck!}0d^w)k^v>&~t1d+{Of?D=2cyngrRx6cQU|N7$H;K%1Le)#b{blvaWy2Y!'
        '#eErk&m(O3lAH4tZ`P-'
        'L|_XqEuKHh(hII1M6{a(M1oopZXlUpP9bV|RsO$B#uZ*A?2t%BRzg!j(Yc;~KFaOXA_q~o0g@nr>fsl|AFyaQw61'
        '@~@?g7mxO7Ax42SdGWy(Re35r0*61Uc7q${O#kX?_a!r^}pWW_Fw$z`TmO^U%!4f*nj-w`95-'
        '$e&|qHe0HPwO`eswuoUPLl#_x|R>waiup8@wV~{6<VP4Lm<o!hor<pVs`7n96xT*(FU%&eP#Sg5*A}wc73>w;Qgz'
        '~3jzk@o-Px9S}lI3-'
        '*M~43?$Mm*V0jfk#lHv*Ja^?H{ZHimjF02@Fn%f>B!=rr6#h)VR?A<K;K*5rwB$kCW^G$y@$6d~#PAb?gXlv%R28'
        '^<MvV18E(u?S2GHdBasVG6+65~(<g~I==vUr$zMLx1$19sU6MOl?-'
        '%0`w58fVjt#v~q4gofgeulDw6T+uh*urCYHpr8e)nAYbw#^0|<*7vgVdxF^#zgt50v^o{L0(2@0J22NL*}Q}gw@C'
        '~Oq-4wJQDi~t&GY>nl-=~*94(nGjZ-JOI!i9`0{MG6U(X2at^~hoN5Gzc|JVO!iPc$JpgU^_nXMo)M_*szgS*imZ'
        'L|=t@3YHv)DrF6tKT1m`Ws`NSDO$(&i^K45clX|GIXLfRFeHw;r^zYV7ER8!RUP!08TFr>pj}6PSEM06!+$yFrM`'
        '2+v{-)Tj(6m**I#6$`4^5YlGMU{bwq7)dNxTd-'
        '=0BNv9|C)5H6EWzM71q&&qP&^*mqL@kNoX@aDL3C+iZW?R*6wdjur52BrR)D>U9HT8S=*Hb|H@x0Y<x1)bC;BE9?'
        'CiBxC9CQg>y8=&35Ts(sBM$TAq=R<=1y0e`szYxcMPhlkeTq&2A1KxGV_2jh^`r<vVC?`24nCyIj*tk4NQKwOzks'
        '~$p?i3imM!WX28ghGWjcR67k+1H%e1p*icnNCNVa2I6yS%y9AaUu04YF`dj5H+@#<ac)jNRjpN}T^qOUY215L#4D'
        'EkBfag~7J-'
        ';;Z5q*B&OBCUvS7O6xHSa;L3ARisv5;*D!A}nix+MZ5FPfxSSs3p0y6$`T~Y{^%I1Bija02&PjG0aeGO!IL&L}{@'
        'T0g1%`HtK4nNNv$tkD2d-LU5sc8BP`>m_k(xR_?#hAhDJq7w(K|80~hOWl@*-$vsy$v2&wa6Gp>-'
        'L)LekF=;jLMAG8kiKKbNOkzHLN+z2CQ}Y=GUE*CjmqTmcx9T0|muV?0k-'
        '}jYFJ>d554EN_zU74+SS;)g^*REvSSmH6>;eCQ{A($ht`O>hd=p}u<>r?ob9kKqN&!fumXO64W|Vnk@eeE5^<nfa'
        '`wp~xl?NIIn{GL#t4E^BLI2Px*u@QzH(w#=etl)(zmnY^@dW!uvS4$3_xF+n3r$lS|A7r91r`}Go-'
        '!n5Z|#iLl(jXRP#wbntH3g&*<!2Aon!F~_Fklynz+`3l}0uRSk!?_q<Ce$#U|N~L&>JI#T=pFu^)iY7@<xqd0k9K'
        'Cz4}_8Wv2V4hq<orkY*aOGcyTm<44&D}lLyEn{KqgbrE`GYi@=O1BN60gNOx;EomqRRCj7=czjhkz7A5_Ko9B#FH'
        'Wnd+ZpBpfLpr0<udk79|HPkw*}`N71C{=)ozkSc*L$FIs;%sJe7K{6jlLp$XIs5J;`>ym+1rPyGe1i3B*i<2R$<1'
        'V_5#+YCvK&2W+?MXMGSSweeZ+u2;@n%$KhG?s0vkd|_qU%VG4R+OkIj-(Tzfe*C%4yJo0V-'
        '*ZJAkamluUpzkt1*Qi4i#fz-'
        'L%b8&{}p?*AUsxZN?DeP3Z}Yp1Lf6jgTIKiv22+bc|p?CX$j1M;9@6n41j#`77wlTic!J0yOmeLZ}#j!Kax(okk$'
        '}cnnKheYx9S%`T7pPUiWnrjMTkef%iyPIxE!6Ys^E!_#b(vN;qJWlf7u7h>Q02!{ZT7gKQ&jIfkHw}ja;A{SsfR{'
        'C~NJ_{^1VTqjsRJ~^80-'
        'oh$<!D#2mD`uC2b?5WZR@uE6>S}81pR?Z@A9*hoO5{`l%1;yZ^LYynAc3PzL>sX^`D*UY6pSiFsd6kdnf7q3H}D='
        'eoAfL0zbDbb&nAGRyOO=(_hiUAkVQ;@eOdzh`KiDF2{JqReTtzMngQB<KUs0umX{KQgt2JK}4$8W^&nL-'
        'F9fy%~qV-'
        '5{mgEa@Z7a>Rc8zZ&%XLJCXMKcqMj!eW&<}PT)2t&+s}eUm#0pK)u1>%<kmJWICFpMafx1wRF@S38EkiqqFTuvSS'
        'HsJ_<mOeYRDe2C!hC3Ie0=j%J5y5@=~IU<Fg0OBAi+wx!)vH3CHF8Pb6e01OfOV5v20VJxN|6#0p(LJn7w+(^p#8'
        '!>Qs7`2x@qcAFv=d?rdjo$`vCD-R}WbHV>OJcp)-'
        '+x}&Wd5pJ2Dd8(EknRpwdJWwkV0=D!HvLfq8bE7%m||@2;M0l_26vcs@}szInU3aCe?Y=6TeaIat8mnD3WC_E9u{'
        'ssMfZ5sTOggMfp?Sc>6IG=M%DFql+i8H-(B@hrlBfh7aNe&RaCX-sLL#_y56!hgG;-9a-'
        'naU{s!q3_d2Y2A6|F3+#b&LOh5KuEsSCmJ72Tw<P+V=yqFQ{TKi&A;204OM+klU|c~jW6T!iY3qiCAAAOA!j3OzA'
        'GoO#^=)J<L>AL*?zh?sv=YW#I0GQ#!O`suqhN<+?;KswQhO8<%r=0z<$!_RrykOZJfPE~j%C?aAa4agI-'
        '5=ak=uvflpNT5Q?S`ipcyCLO|##{K>&9S?TPdj2|Y5&j@6^=+&-'
        'FH4k6@@wrYpX4|K5PrcGoMd+}p?b$GRy%R9tYARuf9aKaU**v_?p5Qecf@i7?fkk~=>rAR?DAEtDI26DF=(o4L3g'
        'yv-Yqun6_uuc%PR?z7%>CO*sj!%@{YWC1I+N-'
        'nmX&EoJf^WW2w=wLiQA_KJe{NeMi&d~>7vE9;<zLvAYKGI3+BN$k)Zm-ZHrs1iu~38A2dS<?gO&fRbk$*|Vt?hDQ'
        '{zomPKIw{aCE(Zir1jE*6u<|ooSy>JvGeMnu1l0w&f~W4K!iYlGvbZ6lM1s@G7j$!zvo3#d~z4<669Yp0(o$54oe'
        '0KOU1-!V8bBKmKqJ6I4<m!k2}4Yw{osR1zyjS7W*bzuzNFBhsk}=eBGczF?T2O52>M-'
        '4g;#1IDISLjkLOUkutS@@(>>rG+zo2%-'
        '&i4asIn;L3ro8@h8`(AO_}YP|UJc`^r?Vf}6a9tZNvhje*J^Nu(2^8VT>jvhS{SHYIXIIkl4NRr&S%HhHt>14H@7'
        'oKg@p8;$IQ^U_R_WnRk+I5`&l3clQnARy4#O|5L_jp~0i|#<{U{p=pQ(O46BW}GNqo%&#7FUB(ZL8eAgx9(7_(kC'
        'mGe^J}Dv&GSs_ktwqG6pPAs{27mI5KZ2Xul4fVyZm#oZNu^n8t=2?(tV5DdX6o5C2SlX;?H2rD&idvV+jDPC+I1e'
        'Ab%xtg<jy&eImU@mzr_C3CV&H0KR#Re@qr>nU*c3BJqvu3v3b4Khu&h1IpHJYULIyY-vt3gs_Urf<6*3G)Iwbevl'
        '|F%NcCX$7iA}NgG6;gz0vqCH&d{25v%32jIHBjEWrR`u<jms=FL<$&KiFs`|;2zmStz_D#kQdH8Ws1HDF3U)l1-'
        'ezlKYC}$tWFe}R?9jz<Iy-&IhN}4u2^5V=>6Nl@*<fJ(YeO>b-'
        '?tUpHzYt4dRY^9u~^w`>=Pb<sQ3!rsmd6@t)Cd5W8lQ<Z^2_>UW|g{Bye#U2g9}U+{Aqf3j-'
        'Gav#)Kg_jeEl3Ir(-'
        'aHoVyQE74=C?wHqXbX5MY4=#KlnjNEOzP0MoaUcR*o2Yr~0^M(b<yG?j^pwF(dFB3PH(z>o_?XF8}(o&&%3HLb|P'
        '7t?km0cIWsE<Ga*e0P>Cxhl;FELtf%}O8nI;^Ru)i&Q`W#$yW@VoYk;pIVc&N6=X#gqNB{KTsd^o%*Y!_3J*%oVX'
        'q?fCidsWm1J_Kpi|mjbnkW_ZzAakwioSe_iX}!csj}OSbK#Bz1`@$JD}TPW$`B*=790<;>G)XjxM|Esv6(!Jjr2K'
        'OeUZ#-s^)d_}#X1SYvlDdy%?45gm$SrT#@d1{(jU@YYuzvH>14^$&rY-5j5p4oVp<M~+aAe0@cDt>6#Q#p<X-'
        'Au}*R+1ZH}F~Xo>hA)hkxD=mKAfda<D)PAcATUvYf}DxiMoSDTTs9Qf*%~~nE8I77R3o*PRU(4)^OA(VP}b3ziI~'
        '~oXq=+tafjhAG$7j>!8h=;(|P$ld3@TdOKdtta`7|YbXsOGmsPA~VJTcg8w^p1;6ps3NK2cjq`n(*yVNxhJ61q7w'
        'Xka|sUfZL+EZ4Va=AT5+Gg7hPb8BG8C#?$l@=u9Nis(VEls^PzdpTuNy}3ahknBGO5cTpjMadN1R6nwnFB7lw7|h'
        'n4KBId1Y84Vu0X!q@9o@YmFiJq93Wk`x)A{A;D6eoi&)X?-'
        'X1{)bOah*jDXp>FS`3y{;>IXnEfPVZg_$eOCJD{1V0Tk@iH<n;Q=sJ#0vgQdb%h$)Z8O?6{4(QJBLY@8iRv%Q?V2'
        'sDx@tTBRNsgR6QsKD_eFTmbK)3zglRHm){rp**~R4?f~gq47RkVd>P<Z+1hDlF~Ksxmu@rW*8cOeoZj(u`t_n7Eb'
        'vw-AMjG~&r<M@Ypo^ol*UZEcVn}5^haQ<{#|6wK5(ZX2e2MAx-SO#t@xq%R=AsyK;}cK>b6BNx{>K@YuohVO%(`G'
        '+?p$UxA)9T9!kPD>Tjc#a59CSFRAC7h5(lWBmCZpw$kp_b{jD>yT7wDF9W>@qp|HIVY*zpT{0qgU5fUO*%%s%ZD}'
        'SYuv|p)G(>;%o$2W7E1|?cisJnkZx3I_tFN!hOD*qp0K|5C)q#?w7W=&9sNMSoKDXisZDGpe`uwEwM1uZVsHVVv$'
        'n5M(aSBnYqjJrp+TCP2Jk1L{{+z)<NL*z2dP?kWNBS8#!#3&@Ukth$EFbl^(3Z_Fp)u<@wIW5Lhf%-'
        'nbF+wJM>)s91f-'
        '(TQ!oFbltC^OBpk24f~qx0&Rc&BhDh3%<a*#ed<Tkr#KQ_oe4G>|v50zL1BOd?$5arqxk7<bi}hHxJ6vDBS+o6hF'
        't!O-{@rcMzA8y!%#EPX2%3ct`o8b48M9HY^rxVLbw2>@@+W0d_Ek4mkJMYXX!8K174&H)`vD903H1e()HCc%`5z-'
        'aejuj?X+x=7iUsCR5=#-'
        '*y}*#Xuo68<VrkaMFpXbFEazR_S{=%Ec^$RD)lh63uI*whcMhMsRAa4dD#lPcxX%<Vn=3B0PHbl1*PNyHTr>LG8P'
        'N=`r$&i#Yrtz2Z;L=&VoA-'
        '(Kc^c~;f{LrlH|JG>Y#rJpi!__4Q~}4!3U==OG`W2w>As}rae>Gwg6C$qWu64y=30%Znf9q@lQw1c^WrD<mr*mYw'
        '8sOkLM~~e3Hwo{3}q<))f4GzaAxJgG0j`K@`Tf#%v{wbgJccb<4nzv6VeucBCGwXTji9ebDcSGso6pNT4qb6&kGr'
        '1)9_O8Z=t6u|uajV*JZS18uB^DCqY{)-'
        'B;Lrisk6;RoaGA)SMa_%<U&Z=CSep1lRt>O$RU>uzT=nIqj48tF})XkH}K60baWqoX3nfbmxMp0*NE|7a@OsQXp>'
        'h$&>Me4oaPirI4|>)X}qB^(Swyo!e>6-V2@FaLyXb4ULD?YF-'
        '2rS5#`*zm1)rVuc0Mmw%jg=`Lrt{vUjoO79+u=ux1et7IG{hAtf&Dh5_I&SsXu(Hn~m|V;-'
        'xD1`<9KC9A_%?C&fwG5kI_l~?@Q<X|rajDK<>|l4wA8m(MEw=cpnS$wH$D<=v-'
        'CV9n@WFI7JdR;+^*J>Z*w%2x9sr4(|kb=!Qu0WwzPx}4!6-'
        'F`rZBY0>pGwBS(}IR~Q$|1&y#O&>>6)^8Yak8uqrVbG{iZl;F9iZTYWVO8Lbs5L|v$gSlU^`>ZoTAE*%@Vic+J#1'
        ')@V9{BFWGU-SNFa{<2BzPEYZR5TmA_&<>-'
        '*H;RzE_Am(mVxb?fO0Q+X(aB_+l`+?AFOdIkrbaI7XKF!9o63Uu2RHpUX)$Ok2?9_IK^o-'
        '~aXhJ|a&<`&@`(RCLg$aoREVvEHWvExl3Sx*JJ_TMoN+tHx2o)?BlfV80s)u1edDzP;jvZf?Z6G|EEUOl&bsw%43'
        'dKZ%00y<JCYPYGH&1G=HZPmRsp_L&klw=XK)6_i=eTtQJo-~WJa*5&n-cW=*nsZ1v#eYLptU)>xlqrdr0<vh?_-'
        'iC$Fq*4+Q#651E)CbBI&ZiC?SlU-xva<tGE)VN#kI&1t8~sD60cO|5fe5fU4!r`CQ<Z7UJIqg93eNbc9!X8uR@QL'
        'O{S7Xyl!G!sQGBRTzw#0->xnb5d(|^?zoI#%i{D#M&8qgedoyE02l4q?sO#_-{KgLC2mCVtsHq-wDYPH#KxjIbLZ'
        'zV|j4T;u-HX$##B|=y!E?jzKyL1MU7F*r`1l!nmE&@{-'
        'DtEc=S#qL=NP5FzLIwqVg=A%COEy$#<cmRgl|6D)PTf=CZ*v(m0*~WM!@qrXB7G}ne0j-'
        '?2&1;#^|KwF51;U+N^F#i7Jyivjz#0=VK`t!uCWFILpYc9B0H=-'
        '8mjWQCV$Q*tE5(Lyk{Mo0E<P0SmO&`RQCFx@^~&ob{ch#I8#*y?RQC%F0sl1gK3~p0ZQm#KyRpCqqgn7^=Mmm4KQ'
        'n-_rk;SG{eI7&i;D1QC~15XjMcrK#S6<Ion$0x=wC`Jzl^{D%&}WZ4{4DhKTr*P#S3P88oxn*tGG&B`D&9i2z3tv'
        'MztmW1UZXy5nNBLJwf(E4&kubQMt6WlLn>&@bLlK*)VmPOca5?Xmoa><plikOgMR&7UEQK$Ty)l3-'
        'V*EYG9EqqtwZ{)dpk{3(r1=q@xLo-'
        '2%ioP7`m@b7N?aEz9^>sfqmm|s~hmf3uk>@$uF`lEf#$SXLG|!qfi(;1!t)as#DABfN_FymC>i5a!C7Mt3Hv!4Hs'
        'e~P7#gKxFICaHGa;~&xB@lPHYs=$eH@by}d`a~qNp-'
        '65^_5sDB2PQWyh!{hN`>G<2SGvQj!sJsvThYz7aQ0W2w}^tphJX1kY)J7o<3Gf2{d)WgF!SoOF|Iq)5t=Bg(nkgd'
        'kD(7X6?uMa8Z6X?2adkVy)~It=C+Tt!%GhHTwuzc<tNSM=+-fenpYHeb=*1QQ2Ra3+>jO{(YXasp`-'
        'izVvT$5YE;dft%~m5__q?i(v{~T8-=5X#0-'
        'T<W;d+U#^$@cJEfFiFf?<F1idtw{DYGrDnytCXg?URJqDWrWH(PKa?G8b)(K*9FVJWmOnX8TBqryR=wOv4|T00gY'
        'uv%kwYaMZ!2f{R{T4(@wg$CMOx;QbILzQkocMU)(vCI6@}$&k^%i<;mc^Ur~<c{A1qy}I&-jKt6d3dmW-ZHM=juj'
        'xQ|(ulzs4yo3iVONPr4PQKm0o`V`8{rU)W_>keoKQFXO#6sqg1-'
        '9`*dHA(bU`=~CKVZ$hfFCC(QRSe%@UWIn_hC+>dvqf>jVtgyI+%$`?|D3T65*1tTL6?2xY4q6-1g6-'
        'PnMZ%8(xczKcL6STocSBO(V>KwX`7#$+WnB1-J{;}(MH~MK3wh{7xt~Ibe8)Qdb%-'
        '>yv;q|Sk43@nD7wh+mFZtY4@m|<s?voSwd%XjBaI(F$HB^W8>_LlA4mj^X4e5cbi<r^G26-9d6(;7wxhV-ocU;EU'
        'f~(0)&Aqw{0RM#fP-0!|ICmb6kfgFSl=lB-`HF>O}bFK)?6h-'
        '8S$&QfJrH{N3>0y`<ldwb5W}wE~PyVsgI2QB%Kr#RVJ#A8rrCFYMfu4HP#KaoRb{^Z6+~soC${sq9%C!)kku=Q&<'
        'FFXK8G61#dpLE_y3;#EPWJPPVf6v`CafYnyJ(eJO8yPe*x@#+C6BLzMaBmO<&z<;IJKY@N$6e8%qLf?>&Db%PNA9'
        '1_#DQ-'
        '=SnK~>?8U*!3Qqj9~(pgnpu6~9)8ZOkVLxpR}mDz5!43m;e$)rf!op21?G*EJV%2m_vM3QHvT|lPq$fn~Q`}vSz+'
        '_B;jT47b3K|Im<bl4L;H^yG9WLT_I;Ps`nu*gcZ@YETg-`l#?cENwt*w-ZzGAUhOlB6vwcvdl~G#99!OWOkC-'
        'P$7yv1dpOy^WEj(JsiV^L?+yG54%52%DzyTd|FZ{aZ|I+utkAX`1hd&h90K?e7p(7+zV-pmzq__Oji(6Uh@F9_;u'
        'T4~BsM3i{*|^a%^?kGgv&FSy<P%E=9`N^NYU1l$!b^T7XjJE$|5t=<lBd71qRRrrKFif~x{mA|VQBkg9J7;opU9C'
        'G*BaIbQ7yx(74u87j`$8PWTconZ692XCzsf?oh#SVsLbsHG4|1=%WPm)>by!^wrw_8=)TfmB9)~>xFeBu3|mlj1{'
        '43^HK)?$?25wj&&xjYj&MFNzFBC=}O@>TfmOTR;7*RjtAUF-UIsXX@E0qAGhbWz$HP<<CRNYj<fw$X7+lp#63v*T'
        '0)g>U!)1WzfnLaR(Jquch^^Q_E{C-SW+Zh{LYgkzgE{T)u=Lb4vzQ9n|<I*5|_UsBVmV~#R~T^8vWe$AjRZl{-'
        'h+7r<}W~p<_{%)o7r?8+^mU_b1XyA8;_jc}$nFg*TYCOv4@v7cJ<;Jqt`T0Gfm{s;DMP&qSgBbNgW+rma+;lLqmY'
        'd8xa)su+-JqWlS{0M&C?CT_+-2eyeTp@yMt4VPdYdg)l){3Z&N?mdjRCO{hk`Dp04KpY#S~f-'
        '1{A&OL|!c@1+mGBlEpk1epD8ZuY&Qo8-}=Ywj~PoXb{Nu4qMShUnlauCYSBQFpo@<WxkkOQ-VVg`yYQ8E{fFft|l'
        '_ugv>Ot8|`48iK;vRckiO-'
        'D&IK6bIu|jJ9u`dsEteE%7z{Z=~Sq+<9rIOt^|f#w^s}>Ez`mAiDnD6<(nFld|q2YLLVn**#uwQ>*9NtX}4UKbl`'
        'ddJoVvaGJHqBzt8dF;t%g&v}yF`7k>a&O{QfR&sDf=C5l^GiH?7_eS7=f_L!?Zw4X~g{Svdaj<a+WJLR<E04;{Og'
        'rw==4vEv{QrIIbF&CVJ%ZhaeWbSw}vO@2WKbKlRO>8Atl}o*$0*bgGs8WIy47uU1yQQlF!`E{dhGmzsSG*J@yK6k'
        'CNxFveD0HrwIN{LIds`OpO0jb3i4{c5krbCf`9awj4mlC6ZL3}o*NEauscD^aN#b>G*taw`Gb5>{b9$2&a5xq6V~'
        'a}<%2N~5>36G#uTCs=k?^FkFgD9fn38sOI_m%Xz3;Z$o)p?zg)oOBj9l1a4KHJ>3>0dVa$9#hj#3iZJ6v-'
        'ynv<;*>nO&1M5}H0kQ!X-bw<>R9T(<H5$)2V*N8G7>{75@C_vlFpoMRBn;G$!69REYdsww-'
        'W3;~6mSQX}1IH2M($MkcI?U-MuoMcbGR{d$0XN6VSLi;Z%TlVex;A_Zy>>*k4k#(-'
        'o~;ashm9grA$V7*|B|;vaLydg`4yKyx+7Vq!{3QDH+{YNX*z9%-'
        '(xbjG{Z?=rscd9_vHN%{wHof>e00lUexzw<+2rHSmAjZw_P_8i6{O83QmeED|o48-'
        'P<!vhnO|3MMt{8&G|>(gB{V`lDsMeJr}qoo8YTgUtdv=y)!rsB`2xvG`6bEp7!DlbLqm8N(nfh8_XUnjCYgJyBgO'
        '_5w`VRzdlFU&Yj;-A}}cfoQp9^jgRLI%(H7wx$vt;S>-'
        'W?O$4JmcjWm+Frx%>EG5v!t@MkeC5zt!87KozIv%HX=FTsWZRF_dE6rr&hlHqf1u9Xd`SZwm|M6o&SJkxEM5|ubg'
        'r<kvZRi2-'
        '#v)!e4eh&T9P9PMxN2ukIjq)1v=Tp?oFe%}UE0t<AiN0nGYjWi_BXm*Z+kBYvYZ}v)jNTzN~~CO>n&%I0R%aw8O>'
        'Sl4?FC$Sso90yK$Zrt#0=iEo9tby5GBd_mf638;TK??rs*;j8qz@$$U|yABohrW<tJ=?rw%2V@5q~4nzKDi`cyu1'
        '+8cWCwy>gBdHv}LmHw(?L42uG1Lg+xJeG;8b>tJsz}3nm0!Sg<#YDRvXR+XU_V3ncrpR)?w7JFo;RR>Vxz<2Pd_g'
        '@ewFW9{6#+Q)+a}H^ZiHl+FIXM2er~Fv{M4r(btkLV6&7x(5q1H%k|``p-'
        'l>eDd&%;*%=);zb|0#lp1n?zU_*>&_ewl133b3FsLMg`uXd?Q~-P8D-7~&&SaWS4&%0CZ6!@xz7-'
        '60JMvY{AIS&ZnyodDMj=jmu9Yb`;F@Y4I2M)Q+yYH4M|iro(5HfVesVHN^_jrDdfoOK1w6r2WoRcoCv|hbJs=`Oo'
        'eZ8L$6j|U{1j{*`K@z~Sq3-'
        '{l%fv*s2iuKkc||L$fFO2*rS5B6Hv|P?G)hU#Zs;McNEHtkFs^hW_R?vudh6Kt0T)l&v3aO;z>G}67I?J#i&(-'
        'kv<_<OaVV|+}Lj2gRqJ#1xwP?)ostAmDU(>(j*_!I>U!tPo;yWtDNIv$`W*{7f6Bb!ZET&LKN2>ST2|nOxvI+zjP'
        'x05N-'
        'H0_xe07kR9yjLe+aI^iGlch^zff7S*|Ln$C*+7^b8<Jf$a0>zc}{1GLLJ`4dISpU}oo(+C)pt`eUn7|N@7i&#Cvt'
        '!m(URZg-G=_EVN^U=PHl-Pgqr|0`GetiA<*<k<iljr;I4ou&NWM6uJk*1?8jrka{)9?t7%rjhg%62+jMI%^&xFzD'
        'LWwxi|CmfoJE(g>PDkUbS0w)I)<ciL}zIqjchb;z+68MHFHcTd|lsxSf>DwH<cuTyp0|A-'
        'p*w2rLio|2*Xc!mH6R|xI!DS`Lf<@`~^#d-'
        '$1ecThG~0<P87$^Q<7NIH=Nw~9kDOO<V9h*JbQgP+f>&h2@~~F|8m*R4+sGn7D;|GCon$)Dlhzf*_SZIh8qsw411'
        '!Q|XVTSL8Uo~<FRGy8-'
        'VTJ^XaM?I)^1neB~Wl`18Rh?3xwh3KQIGxkjwSomH5T&4trwoO5Wha?~=3GB$b){*jwsB?nUiya3PgdbdVQ;F}so'
        'X#-3)(mCWsOo_0k;!IsR5t5JDL3}$eUoa{3n>zEhHP-Iwtz$pRvC{ZZjNzAV4$YP^MYV7>0%@-'
        'I9g<Ovh6B$%^{YL^P8AKAm<w;7<{HQ67kg05hh|Mfy@Qcd^7=RE)1#7QG1237?yksW;o0OLj{nf;xeOj`>fF@ZsV'
        '{;Oxmy`s41bD!HoJPsXNs*q=uBp8Q4%;^Oiig2aN(pwAPkPx*`ypM@n|mWVuvmO!4NunNbH?k#cg_XMc&{Dh?c`i'
        '{+CJ#?61L<4bugW9T%Kb=^lE?qdT?iDx)|kyVw-_{L*Jse|Nh_C!@M1Uc_LU#fs>qe4L}a-'
        'F_^DBM!p7k!BhZT_{tG=Ss#z-'
        '>w3^Tb)d~Fs4n<7*88ZNcaa~LAa9|Id9He)wWQ#`hC}$9Mubrdq!aP&rJ?2CJH83o2>TVk@gczG6tB~&pc5YA<dh'
        '%a_d_LowdFONOvE7sm#wMY73;Gt?+e^C>pDsY4SbeL@z6xF*Z{??2YcFH!?^F%9110a*Zs;==Fv_1tD6*9M#UD%g'
        '?<*&wM`14x)%k9E#4HXcn;VlEVVfl$^8RQtexf~VY<Yq^+!GVg`~Nu?O;K5!b%=%|5E(9m})x2{6rSI4ss|hVw<e'
        '1p|%UcQAunxeWiqLOn40;O^Ieh(u9yDG!lE~lT~2jWHvyG`IqL~U3({FU4AcsmUKHi^|nEF8^aYJn5%Ji0_{e4eb'
        'xQoskHEQ@L_cn?o-^hoPeeX`=vKfv;C_<=(^#3UrcaySI?h)-=Gt5-2xihU^K=vir-'
        'HROUN*ex&A!#I6!afZ0-X)yB4En&Yfv-CQa0)Ic0U<$={xkwQeWcAy9l4w4%ViZL*;mHGxr*D+x3WYarfgGrG#>Q'
        '9YYSSONts9;fKbfHMekt$m;VY1M8iZ_^1VZ0Df4r@l>atd>e(TPaw>ioHTtS$5TY12-'
        't3HT#9C65cTw*fl!_tN96b47`0*CcKw&YlsJfWHK2HVqR&Oy=8_Z2agO;IPq<Ypi7i+jEdz;0Q4^123wVqlx}yL?'
        '&0k!p~N}fd>+VVv}0W{Uuk#vc4xIaBkC3<GlEJGdyIx4qBxtuN0dniRts<Y9A`y2e@ncKllF>K8_}CE$SGwfWH**'
        'R%FvV0eYo{jhLDR&mdD69->9hTaxtTcgZ1>Nhkq$|F!FedhYL^@2l-'
        'hxM<vmP@fe*5ds#{Uwj@MD&UQtgrbb|S*p_5QAxW1IwP20|<kB<=!;@6gu)TR<q<JMCC$*V{m5bLd+cgkg3NM$^@'
        'i3c#ZjvP^Y7<O*kwBw-nnv_yH85c`%0~EtChV6OPz@&*bO4wY*?BTt5_piPJ<E+Np=;P_ZeX0%H4O!n*vO|QQeO}'
        'meMl6ItpETwXo?Mg*UZKv&T}^cuO3()^VR&h=ksTS3BdL142%Y(I^{8rM^6!YB%zZ72af@Yj?-'
        'bXC{s+q>QD56i+)cS84p)S=ILGQshj}WknbGTI4~qf&34<H?ZR*C63nKsSSSwNQK0%hl2YDwD0luq=?`YLz>Z#|;'
        '}o{+VLFg{ofQazf%mGN>{i9%$FC4b3ZH2nFvA`!lBw+jNicQC-'
        ';1ief6k~m27tv}bD+EoQ>!28S9IUxJIG2<EXyGr5~v>S$d|AO0h+)EWi&rcBVkdFN@1-;o{`{k+8D~ZB{$3-'
        'GaW*#Hp`0b$y`aPVKxvs6YFX$*!#M6(C1S$6Z1VEpfFsl6P&9FjIt8zpq}tm(>8${Nd?B-'
        'NOEZWTCW*ArHz;iP8z452!f7>j)ZfJ3}zz{0b?T7QpHm;qVSRlJj`e%0)O~N@r9fn%ttdY%V%FitL>_}dc<0&nWr'
        'pTlZoAo;^?ZHiIlg2W-`Xo&TgqP>OcdkKtyPV-'
        '{iGpsD^aC$jB^`eJFuzb1RFIs?OPA1e5w=<z2t(^?FpUiw*t7ckydwC03^rH*6Lq&~CIY1qe;IfP5M5il$k75Eec'
        '+1Q#d4J(2$PXXgl_Eg6iMoscl*@><-E0*d=mwkkorlpn0hMtWOb{W9jxsq6^!4kuJ6GQ_tW=69L9d{E`H$BZ-JnT'
        'ISa%*Ig#BZV`q3qoFcDL!Jy-'
        '!>+0hl8)lEGL=CF*d9)i94Q<BQ!azF(~mf#yW#iN;%%;9;v5GSu`rf9yX<jBTAVs3Vw?e*jOHkk7#9~J2GBHUapo'
        '$1_?<v0oc2=VF-u_e9uHB+Z(DpQs@AzKC@bdBc$l(Bt6GVILf(8dYW)C4WeP0llZJY@}`yF4yhvebW)_SLFD6T41'
        'bLBvx<(MqLFQcYeMVareiIK<9B4ZL)3p154oFOt;u;PZmvt9*+g1R=v8<)BupsAi)##zY~ElBkqF70ueF5PVpc!P'
        '+H$1rquvtdNq&`=a^l(729LgK#UmM~@5C{L^&w@d0>}K-'
        '@qXGQR~{^&gR)tF<>KrtDVE<Spnf@vF`Je%a!zuW<AFBkX?xEh)QF#-i|IvAr0`0lYD7D?4x16G^ip0AiYXT-fes'
        'u6te~BP_?=q5{;EUCBhVrSujgzBtPY5x%W~7&o_<)Pqs1_7wSb6{kxA!)pV7CGl>4}1J^1fne$_cMw)O@x1(?}a%'
        'uerR@JDl59eg$8zp7FZ&tR3pLAjh~)8RZaED{lm94Vu)i=I9ODoN6Dq>U}B%&Bo8>I+d7hHmZdu{cJu!<U;H!99='
        ')f;b6afIP3+NmQQXciHJPc%U^Y8ySbOGpN!);#Y8{;ufAmZq&8-7>`et8@8~7)NR;U!?O>oXBg03@1?p4thv-'
        '$YtcQZH6u#9peK|tHIFd=iUV++tq))A6xV|KEqSYY+tNy{B1`l1EU-0JXy?Y#*8a%!<K9%-'
        '$+IL9ZZ&<nbjI)4Hbo<$Bv>_rirlqKt=!&kUmpY~v*rSU^HMtur@=LZ&bxb6IWDTw10AG5AK;`oN#|=uRe=tjW!E'
        '`@vejT2>Azw>*LTc`)2ei|hMiSBW%!1z-'
        'xhp5bMIOB0=I3P!lp9NMjJc+So>u(u<*##fNyJUI*%PA4jY643+j`!)s*m|1lf%Kh}<&6Gb50Nb}&jYssXqD@Ce?'
        'BdXcFYLY_Nsgpk)58UGL19*S{-'
        'zFefjseu(R%;^cUaD~xNhQr0#VnUvZ=ny;^2(=(Qh{vWjxergI5iB&6=YEMEhDbR9K#~f8%o>Q-'
        '(G*M^9smY*57;b*5r6mN<2TM+PlZ9qC3OSr%j^V${A*!eZ#Ga_8RwHMA1F_=DsEC0@!D@hZ+js%RikUL*3`6)(Bq'
        'ODD>Yi1jLH?!^0vv61P3T9KzB;d5)3atw2jAVurC;m6~DRjq{hJ<xcJnhQZ3gAuGY%5pWqx-'
        'I>L;?$KgwlvYmX;IWpxEjMarI=#R(@pokBQhO0i|pR&Q=)+n~}D}{hFt#fb+I~!<kyd(8#EgaC_LH!#J7(5P#%vO'
        'zo$bUHid5nq=of$t6=Wh+XhUTEZ7nz6`?#M^e(Ke?3xcpPPgrD?Z+Ckwjcc&q{B<*;ZbqO;p8Ow_k;e7Cq?_R&^m'
        '88aJ<7Mjrz8_#8!b{-'
        '*J32fRo<RqyKlpIN$&@I^Dbb`JDDl80`*2CRw!jT<$6IdS7|MFsZez9*H1@UEZ@TXU551>s12kD3I{dp7!N44vN;'
        'H5Bl1sqo(n%iW*I3#$ex-'
        '0ycb=$?64;j%3X1tFq8M$SF;UD7Z*VS<YIO*^rInsfIQk0)O;E2wt&_6uiHv+AAD>meb;z^wQMqT@q#C~l^Y-'
        'zDK_(Wy@NpgUFgwNhf%IoeR49V|>e<#w+1QO<yn6rq?c=BKU%Y-'
        'bc>m+`w=W;>58gd}y#L&504o=hkXXq`{GoLMNw%zfb9N>oi`-'
        '7qLX={d_2^g3({h?$$b43K$wdgAVg42IX;$RF2zBCD@oBYM*_qi+PUn>5_$oO&&PV~oOfVfdv5&_9kYa<kaSbj`P'
        '6ehEEbL|>kyNwOiBzQKGMUR+x->C8Mn-'
        '$nv*F}?uBl=4r!I(idKZwXUez4~23N7RP7d1M?H!XrixTqOy3@IRt8@FiPQQ2SZrjVI<?};b3QL`z`Gz|k_9Ak(O'
        '8=6Q7P2(`wfzhTr=y};KFMYQ0R_zlXGvM|%k_hPZ-*YX|BjME-RmEkK!399@Qc0rgzi2s?INZXYpI;W0bw_ieNZA'
        'M`M1o3Bxg!Yw@N!)H`#95L-)pRJRXn6J7i@xInPw$S*z}LZ#%;DPA2iJF5afpv-'
        '!L#^Q@niIJ|Bvv!8B<?hse@&MW3&?S}cISR-'
        'u1bhk<hIN!5!HnKg=wKikzwi_B;$TSTNVThP17f6HcmW5n(@ClYNshBDoS9tT43+&1AX-aN!o`xj4kktY<_K?OTa'
        '|!6dNQKE)ljODUqMYYv=unIf;UZKGJHWs8k>O2T8+^t;^w+C^_l~$7um%=XuQVV@Gy40`e_cZZeH0xiCn)z;p`+c'
        'S#N7s(yADL4F#gwUI_*!O{P?PblrBc%(?dO!&tX?F#IGGj=-'
        '=EHMnWN<1~&~q3v*D*tJCnBXm?QKsdE#6rG{wG({8V?G)3DJUY%FV-'
        'g!P*$aK%F>DJ+z)X%PPTdhAD(ItVU>nl4Wv2xjw*N3i1(@R4xBfaR?u5}YG(4(D5t?TvAz}T48Y@k=+;1VY2*pA?'
        'YrF!VmekA_nt-=wiG6<Oj%_U3TEF{vUn<wBa9yH;2O?yv5G<-'
        '44oX*^XDURvVyL(tx)D)L)Hoo#I85AjMflo;<1M$4ZDU5v-eqim-'
        '`piRU90Hk7@#us1+Ce9vPJFUQA3|dhH2kbjK-_Nf1VnR6G<*WW-*Rb@)1E8Vp6BOfZTN~-'
        ';<7?*v5&kxR@p)HUaK7mWWizMhn1@5Pdw-#rIOImL%U{F|E|Gy@3u}KUZnxA-_UB!7GGZxlIod(I=#W{bjvTk(`h'
        't6;<1C;jGLS3`%jXhM%VxB8>7FOIhj60vUgcyjh&Tel&AXSr^yn+yHdzQvQ`gw8eeU)?5le++UrNG^QspL{8wY-'
        'a>sXK)Y@LZR9G(W-H3T(R`0Z7A)%gFG3mmOcechmcLVQ=-'
        'MPKBwKKNf6|2^NjjsEfUG_B!?yXS9<xirL)V(uey)sh!vWQG`UX%M&bj=h*%?E7{kbFX<2AcaUi5YP_;A72L#d#R'
        'SJO)zn0LZGsRB}LcTYucx7un&eZxya@$VYGC&7VcMOV1+Q6VD>t*`{X^zPnTT_JP`Frz-!da~>2<u}A-'
        '3eGftAmEPnvgkxILK4&&~B|&GF-!z?kKa@_sK8gI@emh=;q|Vw)8|2F#%j~>M*<(?N-'
        '4;yOC#Ku(v$z~;Qv%1h@0Y2EA#AR6HNT+MB$V}k6?g=*4))e{VgDM0-'
        'O%2%7WxoYW03&Zbcw)m^63s@ss8v?ydq%V5hdh<D>)a1MKDB43OJk*SN72?T~@x3!*>ow%7zM=P|CQILhJ-'
        '@G`)=X96FsT^?WiNcCt+C=7o{%kf#Zsy*iHu92!n;_@R&B0~KE8|Fuu}(EO}>!KfBX(9)Z_PWW_<0t{}w(b8Yly;'
        'St6sIZy;ha<O$yG1My`PS-Vh2{=NXf0&}HJXUMgy60pjhWI5B@a8Udw>-'
        'Kt)GL!Bm(lmr~4ZMq{kW$*qwQh7>CBe)}~+EBa?a7?0PSg(R*ZDB6ITAN4zjbk3*!itEHg-'
        '#Wh#fo?NTQoWv9`7{B!%g;wI$8;x;h4lqmi63%om6L4_Nh8ek9Mlnpn9Mo;`GI0&rY1$kk@Nehgb>Wp9SpoGJEFc'
        'U)4PIQw3>e%5(ZnxITgjU^@F=iAw{%0X5b7sz@9FjM(R1#d%^V~e-'
        '(P5I3*<tu9K+82@VjfZrx`!lw;d#mFH7L?@o9;*mD$4+>eUw}ia-'
        'B*F<%89j5!ct{f9BF#^2<NGX7vb!RqGDqVA(Iy?BE+WcYy=SV^P~+vMhLhRuGWQ^#5r%X5L*t#C#4lBK$G9}_8=P'
        'hCR7L<S4|HD+rTVU2wNgXPG*QN6TkxyZtPnvYdJD5>rq!)~g*MaS7?I(p?Kp1NNP;y8yTnM@4~Q3k~OITc}^ukzS'
        '26r1K~N<=NueBrOPQHWNg!%z8*+FI^-p+W@tlBUQJMQ)qMpU#kin-'
        ')4epmYrQOG#d8D}}eT!|8UpWm<l;;iKp$UCDSy>6k>3?+-%@`N2nwSlFhq?2XVq)px0ks-'
        '!0W^WW@XMi$B_5T;)Q=$+IP-'
        'H=HcEXhFNBA{d;x>L34tmNARnTXl$9<_iWQS_#X`cnxa6t$f;I=BuYzREGjI&lFypeqM@5bLwWJXR+-'
        'y@bU?2|B9)S$SEGAIUU|h2m=K0RI+4?u6GORS?|Et|P4YR>q_Rx-NE4zKK;NlnP>xiDwFWlzHt*MthpjMN&+GY~`'
        'bX<|pCG8W<u~A>FwoQ`KW0LuPfQX(vA*`E(h7bwqbJ<DE$|i3mm5N@UYE-'
        '!mjFENH5WcIC0j5&X7FRpISO>^B%?$;mV?(G(x>dnBz@TwK+-nfdoK?fW%;7hcDX-vxGxPX@Faz)dD-'
        '+(u{ogIH+S9WR$)JjB41<7^^QWyAn_fS1^Xcm+g6ODK)h4yTw*k{K?%!-_OTB83-'
        'XpvEx7>x`+q&ykr%<hW$CD0Kh&Vk#bW614;4qQsB%K1mJp(pA@RF0w@O_1a~`wYZsQnlxSL6-'
        'tw8MqpiaQ<_Fm*74(oL_tsh^4eY^$I6Wy_LSfjZtE?slE7U#okWn~rDcc^TwH69m?4<W7XJ~ZU_cr2^;NK!6+1Fk'
        'RPkRH=pDH(tZTIkg7{jzEGo6n4;cOeYX%cwy1GO*{6Lc0(E<t0t|)b#LglliRgGkE9MC<)Xls03ZNU*(V6i%KuaQ'
        '@Jfr}xSlw}4DPV~N&?$WEnIYd3$>Yg_Oci4v^7W|5z=kdiDfphs}iFsN`PQrWzWH%_E$znqKmGV=k4=j6t@;i_Zz'
        '$<c2ls_yRm_C(Dipl3(`k0)Zd4|>E3TN6D@s^rOg`!Eoppo9?owL4t7j6Fmqgo_R1QHqyvX*LWT=6vtuDmIBDWSX'
        'WiPv3~my+jCFa?dav{_1cAXj)FPvr9~TAnBafR-twBg<7M*HP@J6gbW=Ih1UQnj%0^K?JAi@B`E_X<~$r4TA%vJ*'
        'r0Z)#F9pb6v8qYE3kI*u22tGjakLO-r)WR1n%qIBLh6+xY;9eo|CppB+P#az-icuh4E<;bLNCcrswC);CHloba|I'
        'S*#bSS~{lDO<1AFilz^eIi8eZ9y>AYxNN^DW9GNxL+V?3A>c^iwTeU%CadWRlMlf+7mbx{eN;QpKZxhfgvb|*b1z'
        'n_JwE(HyO&QX&p>6?jsMl<na{ne%_$1n=o(^fI3$BLVEQRAoMM)jPl{qKVk+pu5Z_}8Uz}A~X3$smg>5vG8ltfIm'
        'h2HcH||Hd;$696cIv<(a(CgE=v$t(NPIJ;=!~J=3*hsuXOX_WGQJkVAdl(2bP$J#k=~WrfY9!M0onM#4#s77)FB>'
        'o8AzGr(ozgAB<X1MwDg1%#6u%l<+g;+EsNa+Yphh3!UOz8QTb#vXC?*FmwI|wbl|1AX|udGkpOLOBG;<E<t9&nux'
        '9eDpwda<v*Dv1OcAch!5(h#QK{Jd5z7lJPeGUIX&kpmScFv#u*|KGlTuY*Tn%W1-'
        'F2^C4{@^`g)6q%h8V8Fc14{@D3Eub(S+qWGO3Hgz>yKGfdlh=j}O{MEoQ7GQK#PSUj1#+hyM|tWbTV?jowuWqY_F'
        'SFRd@{*t+tJ4p6RNUSa$$*<C)t@~Gz~dM8E`gL4B{Jp8cQlO-'
        '8>Ns>#_O!*0%5fIQ3WUQ@7>)xgYyV3A$Q6QPnsF052-HC@JJq#Z{F1Y6n3Br+2b{8n6oK9U?r8v;tUd-'
        'b0wwRyzEn`$W2)$(*a9&W440KLP%EinN+1!TJ(2v&7E6p=Sd8iIE=QL|6sMXcg<XCzudcIWVn0_Mecv?=bX&SbjQ'
        'O**#Zk}nXUthghifPetdt*?IvrAv+^2g<IZH8%VJQ8oGR1Io<N?kvjE^ohChQEgQn9dERyHeJA6GYd))?N1&6yK5'
        '8<nFca%B04nugpx6*UH<niuAQ6>8OP1PnQE++^yN*tSf$<Icr#?puvzTU<aHrg^^FiS}Sv;F>#xE?zwpWrOWDFrD'
        '-$mJLI-^qawD?B;dsxJTKp{e-'
        'p~{{K{0CT{^+Dr!MKHu=dfY;5D(sGggY(x_e`GcnT!NM2TC9g*HwL%&qp(ddXaZtkt${?V}=XrrBOYopYt*L@6DW'
        ';!bXVY&+LOwl^mI`G)H=8&n0_jz_O43Apq6s)1BajS?qjk*lWG6X@=FSpLP7+f590Y99rWF?uib#A<c2UXc&CVNB'
        'LC-2_7PShs6m?~+ZJ7}$8omJ%8sSjQv9C)CSoGIx54!Um~3KgrlspdTe3^-'
        'p)#d8jL@QTH^tzLH(Go8}o6Y_(P{RGceo9d%yj=Va-Sh8FJra6HL}ACzCLPB;0AHewT|h`+tiQITPLPk<0c68p-'
        'DD)eZB`0aSU9=*z=udhrTOp#1K&=!k-bkDMrLfp7VwCAa8k-'
        '|V2ucTv433bZxlF~z}SEI=CY)25vq5(D<2>Y~~d7IycR=L`m90@+!lE{|>X}#MuUuY$iev-RNAWIL(G6)0{^DJ2a'
        '`z8CEr|k<y**0rv@s7Ii8dAa@E+T$Cz;C@})Qz?d#ow3oH*_R#<>{k*;aWTz%DBk{b5_IQIxLll#EkT(pA?66XZ;'
        'X;cRX17br8dAK5VayJ$y{;YP7G~K;dw<H=RSr1Ob~r*&91N3*4HtIxk=U^!(-XSMRHG>il|!@gIHuA-'
        'RNRJaawg01{eq_ABR=M~_w}?KxT-<%^-f1n|g<@4EH-kICmFlTu7s3V9RgfbR5~8Qx)lMmTJbmTcf6JxfmVDLo>j'
        '9|yRULbnqw-N&9Ir>}76upJ75m#<6l=Q1{-'
        '8_6+@%{mletjHxsVo{vPlK#TLk;?;(B`z%yKeBW_)<l!I>Djh0VpYYHz(4E|vU2?AuY8v*{cs0fu3vT{`0w(t?kN'
        'r>=NW~ejfUjchocy;FW5R%|1-'
        '~pL|jaV{(&<hQ4}+wethZ~2*)LC7WhoLFEIv91flNST^IT6?{Tp3E%jy<{r!LcFR)|VO3o_6`jJ)xj>IK%qn0ci`'
        'I%I>zF=r|nxyG?`#&<YT1ET%Pi<{5DMF%STJ5a-'
        '5FKX~Ghk?aWCbbO>08Cx3Fvw<Y=~Y5iYNI=Y{%z{LYciG(46udR78WC_A;%4-'
        '~O_yCEsoQX2w@v1zobH9~XXU8H$$Inn!mvR83^{s<CHs`#-'
        '}>E`QrIS)c4cgn{lx2loDR$ZI%>vjPv&{O1lF1HK%o)A9Q}pUgAsbll`veBW^t`%OlfQHq#PA82-@Xy-'
        '+lVY)8r6f|vmM0a)6JnZaQR_Zq-nEwOm$Y=<|U~1e&3l>eypKX67A0bE8PH6jNo^_OMw4ckXQT<9Kuc0<^Rfkq@q'
        'x)}R{@}<2>>p$v8?lk9>z(U|{k_VScZllTiuLn*6pK61Wo;{c!LwO2X5;_pxMd7i28KS%i&PDHp39YKy$d5I7T^1'
        'FNa1<`xJmxRgRy&x;r1BISq66NEjDY)`4iys&`Qk6iBig^X8(DChtLV;@9S^DN!GH~cVA5D`g-'
        'XeF%~i;sTq#)T>U9<ym!yVu?odfJsMoyuOpJ^G;4ZS&K?1b_;lie1zDa6BL}bClU646{;Em5D*n<hs*7~qnhrJ$k'
        ';wG09X;HWtntk^Yid5&i`>_wg=mm?Dxa$d(RTZqxcdz4>>loG^OWFC^-'
        'nM0sZoaqVYgj2X)8r(7=l!6*z3r4`7{@gp}L1bkzFiJ99_rCed7la?UQ(GRY|>$<j!{ZQQ?qmR!xF03Lm|3<<1fg'
        'F8<m?#S^n}i7TWCR{Y=p^}oWJ66=^WSu7r7w66HHvXV%uSBk3)S<GC>6DFybh5w>7bNw_khy4;2$}rOE4eg-'
        'Dd-)PAc;SZX742Zd<@ZH?_D`VR`g4AojnaLof7&{(Z*74gC)0XC)4CE42J+f_19`X8ZwDUlMtYPg&Amk6up-qm<y'
        'aQ?`(2swUEEYzcc{|A35pv7X0QOV>Ba^eblM1S>J?raFCE3g^&SYSJH~&&E|%ULz~oil9B<`?r|hI+6+IPyNB8dj'
        'o|et`uw>XX!7*hu5vvRjwH5CX?~8d9g!Z057PG88Y<Ad~WC>;03j+R8PGkjSInN=`s;C;aSjCtTCu6Q0^|ozBnd3'
        '!?`G3o<KBxcb+4EXA4iS-AqtrQ!L&2CL{3q^278^P9AZmgbWcA+AFE18zYK2<vw1a@Q`Wz7bx*nh%3((H>0o}6z-'
        'TMeY_bfp7t_$cmnU2Va%fLNh-_`)V69j5vn(>N^L4H0S_agai4dku%ia)7aC(IcF#AUmlwxf=JwbGq8&}7-'
        'IR62XQ4sU1=y{5HYk;el2aUnFSHx#wvi)$8Ehf6P9uH#m#D(KLzPQ(t%^0n>oi>~T$O;zsK`F>da2}P!Dhu@HU98'
        '{R+)7WHv5FfC2@z(}EBg#A=8=@2})452)X8CGf7dPw0Xk*8j=O-'
        'tVR9kU6k*K$)FlpDgfjBp{%Ixr%1!=Ik(UBT^(RLs%0EVUjbhX{en_d<uz`kQL&h{FZ#`x6`XfK(!y0EG%8ABMw!'
        'eLohwx>I%kSy-v?2*d1&S(Qwg_XtwQT4EeWdsy{L?J?lqZVwFq0^d^G~Ap#Yz!NSb_W(lhX-'
        '~ao>J+!>u}?iuO~YGLKe2_AS6A9IH2aHQk7Aiq>n<XCx5R|TQw@{RM!3cq{~b}!@LlWwC27lCVTEFZD=sbPng@qf'
        'VIU84|R%Eg_8M_bigP%E<qKWr;&E)Q_jk1ftszxMCgnIRevDMlaq8HnldB;*D5z7_s;Anj2CDl&5;5{=JR9p{Bo9'
        ';i$Y?9Cgs2Xpa0iZ|M%5saW@c&%K-'
        'jwt3Mmg8B%K;KkAVIu9K*2<E=s25F2FH5hAlaz*d}d%ng}!<y@hJTltIlDyY=J58}6q+>uhlZJE)rYO_rFs=6an?'
        'D{{EH@ssew{F+o+5?NM2bfhrw*!^ZPnlPkhtgGDtyABpuoLy$E)1QHDoW-2Va_ZyPXb1%D-'
        'A3ct!TS_XsMvJ)iGkyvb7$GWMq`l^g0fK(FIIUl%I*mrH|7wnz+&Eg#Pxz$N$KVfq#yV2%rsahJGNzBVXO^lqSRH'
        'wVV@gc+cUiocBG_S(51u;|=_cDY9q@2A%IU16FUL)thI{#%V|TX=p5@!qo0L+4@)-nE5Fg)VcmL&ZZ-'
        'M>Y#tW0%$EgM&fvlJ^9Sro$vZx`<I4cXl<`4AV)~bbQ9h{Woh7AgKI;9AoMDIX00>2&jBqyf_A6_OXay%4;(_Ui;'
        '!CR$&VY(6`^zLKoqP)$2E}qMCXmb#J4xn$Uiyh(6;N|yjwOWc0Id}uGhr=6VTQ^vb{6WIUIjn)A|fkjkq+&Q{a4&'
        'Pf8v+@AeR8t5D0YYMWLf;6&~>>)*=};B}6nQI)4Qe=u(TfDpK^YT%)0_1b*%O%yowIjcm8SKJuM_oB6yT8u4bD6)'
        '!_f-B#Ef?NjI9XAAo9U(*-495jRrIVk4W-'
        '$HrS`HAO$a{g(b$l7O1<_Swe+5y!xub%pPnq^UyLSR`(Xhxs{SpDsBIn7b?g<U<)h!FDxcR!2halOfH2aWcl42JR'
        'd*U_6HI<fuXPWqxu5*nWdc0bjHb6@_#b?8m)+Kw@-'
        '$j?~97F?`&m4;P&0^5($3*u+_#lZVbu<V$DD!*C{8*32car{gto@j8N4H{k0Q|Z!)PMTVi$rGbgnkeD9pT<?{`6l'
        '&kiC5u?bP<>-ecR#V9f=#wLEKYu7yb1GeQMVZ~OEo&Xc%uGu%oixu=V>#f09fh)(FFA&NG+sHPT!%g`-'
        '#eUqhsWsR>>&=oX3OrgFk)t5#$$(m%uM?ko2=7sPFDTPNpSm1bRNA9jfANmDfv5-FcSJo(<-'
        'ioZV)yr5>q7YeVfe+YYd@^WtPnhG|+L=Y>kXRSC?}*6`!-'
        '*%OY$<by?$WiNVSxz>ADqD1(zcTw;a>9te1>x<YojWzj#f^ZG3(0F63-ub&xl>Jia&^-Yp$hk2QR#w5i_W-'
        'M2Sd$u^u+JH;6lbH4U&_<>glV#+P!~>uy+XO42$g;ya6nYj2t)TliN@yuiL&;w7K;Qpt4m1x|OPz+Do44akh<7=6'
        'wwr1dK0vwQ)oXg?dzz06`s^BX5rh6zx20+8yGgSk~dDlJ&(YKoxJOJa#Mf_~gp7r_I>a?;QmL-'
        'g*sHrK};+ZZ7du#2f8G~9*r%p5(z{g}+k7@-V;R>UtynoQBnhz&7HrXzH(13Z$VOffKFftTY^`pHa-cy!8u5q%qD'
        '^msT2^@(s0+ZkX8)FOP6$q<zc^xrAb1m2SG;{MNni=+|nCi@J>He)#^g{6d!F)s|zA;;{ji!<o(ZHitq(-'
        'Uc@EY$!(Z=WoCI>i~RSMugp$;t9DpYJxay#+ICdr1X_FOS@)H^`%ACe5$~<M;5DA)j5-'
        '%wp?sLsa#a+Ub@S?f}~!=q?Wr7?{I#_oR-'
        '6(!&#`rz9MeR%5rPbn6%~3wqWTzVPf9C&WKkfxRayK4L0%_R(DEmCo&HAX$rip;hhD(7qk^R+bgzNU$SH_9>rup|'
        'oR?S4|!=Y(u}PF&dQn27k@jRJco_@%KZoJ(|P-'
        'G;2M)VRD~qhHt*(qRRAn$y3o*x^7$QmOS!EqSK4<?7`>?JcyWVUIaPYemG$#5*6f0$Z_Ub@7lQ`Hk={kdo4C%>{P'
        'pA9`A?MCp21T4G(BSj5qNtCV@_hA6^PAg%T~6qqtdROET;%Y_1#GZj3jXQOi2Mpww)~p(9z%%B(uA6=^vG+9DGl5'
        'oGMgxdwI@vHsKP(H<5~p@@g8L5toya^5IpFUI)}$Lh8apJi>rNx(vK=UIiotU1d{r_Ad)JX^P70zLD|&#;%FM*jS'
        'g-qYciO0r~74$)Xe)Jw6}U^<z2CswK?<+=s(k!%&c+TW+c?-'
        '?9EVGlab5>#DWIF!TYoU#>2dB`wQg##~nW2lmdu&{4n^$D{QDtRypUaYA~u&Jtj;~GCxNfNzDfuq)Op%NJ~n7}!p'
        'RSj6Vzu}A)L)p+DuW&v&PsKb9bY&;mm%QO_&=9Y=twBjTP^eIHjQPZ@`DGwAe+-'
        'h*c|r~#_8q61cT?WBQ<gg;envKej~KV*Z6cC>$_65Zt&CilgSuzM?f1yd+OB)#CYY~>d<uFg>e!-'
        '(udnnHF{yGZY%e7I*SRnmpA6$~a%2hr^U{<4#>K>_j+nB5Ykw8aKuK0mV8}2lEjKA^c15A-'
        'CM*h0)5)ld$sUwU&>w8!5XR&k$s;}AEE2$Qu<GAoqzWg0*eu|5P^97-'
        '&Y>oW0JAumvfIO5W}q8(qFZg103y(iYsR6Ld~*6|@4%~qfBzq#+U`lshmvko5ao&GcO(NZ*w*AlT^xOk_Xmm-'
        'I`JKaJ(8;4$BUu^n?<epKGMECjHj^1K-'
        'FNxN3mi1_8i&FzA<b*K|b{OnXD(aI?(CI>i8W3?F+g9NV%r&?fl*Y8nyT_?eG7`e=%phcHGh1q(=cpTd}c3&;I?t'
        'v%!ZMc{C{hd4aJoXmYHl>N=<vo7cl-xR%)oLd6ROP-UG73*#)B3|N!($T#iA8brg6*k~q}Kv_EyR~W1tMHBF~(&j'
        'dIW3#WsxxltBb;U!A<%}Nx*zWKYT>%nkov(V~X=R~qRR@N@5$M`Qjcbrb+68FM)^$L`A+QW;J9IVc`e;gnr-'
        'I83<Ko##29VE*lY~{EZ*8biR;m_cI9rr(QcsiNsW74ap~SQp8NSHa9Scvw87U}O7p+}sfm?VlvUf#<I-'
        'F#n_Kr;c7PchN1V)`0i=eRB5wl)o^HaHrmAg@&L~{u{9CVE#_~*PM#A8d=00Ay$`wUZ6^kOH|tQ`F$`v3>N(>xzV'
        'Y7;|rvnkRSpISmsP29uI@WEditP;<RSikWR2TpnTW}#<<kwIM9l!tG@uh1ox6N~k>Q5aS~c;DrwJ7i%0EPr1MuAs'
        'buwl0csO((Z%IuTyGrmOY&0Hfa@1$tCREn%w*^`|Y-'
        '12<bEBim!!Tz%b(NNtVNaMg!vMF;wN&466Xr0Wyw$I+Mmpa0e<cCgvLBza%DTF4MXUouyr=F0qrxK&?5lQh?N&=R'
        '{2GY!@INU!&eUSsI*G%@Pi1l6sXA2h4}=^ddBx@3N{d*2Q8UGE9aM(?+ET%o<O*1JN7U7)?om4?pA!YP?G^lt0yt'
        'Cx+yT20#(clN@Z;9uFZ@Ai#7EBJgD_Uw*qT^{t%-'
        'L+uGH*a6OdOvvj<KwsQ2R}Z4@xzbrq2ryte5uN+^ZMnR$8TS}d;Q8(ynSaoRPoh&%uoB57th}R2$i<KyBGa2x_2k'
        'K8Ex<MZr^vV&IA6OnkJ)sxWFAgaP{A#XB)aRXwe-n3fLks62*7|Ov%CEA-%fUD^m1IZMj#2$z(!3%G=|b-'
        'bBcx>GCi(PsS=Jx@)XJ`xyMooDd`u;=PG3d={W$7ps{>$-otUM-Et-|Lj0q^&iS?>Xho)eXt9ZINSzFtcA$dRaM-'
        '#yH1ds65(|%O(OP=t}6@{^C5Z+$1%%~CVf3y@q777N1*82et);$r}96)f9fKD9pR<Bt4Yj?9QKN{0p>1Tp^@k7E1'
        'q&h*Fyzu01Eu5-J9q8Ic89n<7ltMqvX)`2R+KKuk?V7jd5m8E=>c^7UaE=kSbF%O_XwNA-'
        'cblWk{%(;y#|-Ts>p=xJXW9Xsw!?p7id(sh_5=pmhtcG5jZ-(qu&Yi-O@kIm%a#sO-lDjq`lo7>KCMfe5f}8@`By'
        '4}X{L;0`?}3wsi&(k8$~jjo)D!@%RJL;IRwJxD~x2ZUeQD;-'
        '3KIw+#X28gW(Ni!fcEg#+y3J~CGkxlB`XiGlgDp*>+-'
        '^z^X#IY!l@xoOQrR|i;=W_*Ofn7;}77jZ+8za8v>x(|;nNDgP_OP<H2?`o8+eB@=OHI5$-'
        'S+ZJ*_}~(Ncx9uEcnxR>c_7kp<EU6eky!z_9D9>yJr-'
        'a*WL0oolIi;PNrf*wr*GajoqN2(|wA(o`ifSx{}#B0=sxe;=A%D+;@a4frP1e)XAME9`a$gR~yq~aU-'
        '$*DU%CeX>u~irgOco%a49r(J@m186NA}iZD^?2m@VRHeA;{8N)hJt$pgWx&B1eD3~1>Lqa4o27QwximfJ~=Zz);9'
        'n~;Br^RnL6#0`r3Sep34y`5=mg7yJoGS4TLc?tr1c|}d8@M=QD7Ii(^=sNNwbdP#LcvZsZ^P1Hsu~OQLFIXmm$2k'
        'Wgon`A=V^hPu=(=h3^yk{dz)`>#ce6&yJR)3*JMRMp**YiouH%p0gqA9x>8(mrVR@&I~i_IXT8PttG0mi;3fvh%;'
        'pboJh*wBkCyoF>HKW+@J1ZRH*VY*3_$H13{WGE1&RaAELU6<8H{v*RpY}O|1bZo+r0'
    ),
    '_portable_underwriter_0e3c6ff3ba97.reporting.diagnostics': (
        'c-rkfYm?i^ao_nXVB`xSaj9LMbdDJD%C7jFx{4pko$W6y77j}exv)Th2av1Xlh=PM-}B4T-'
        'Sg^s03`S1t5hXhDv=z_^z`)fYkGPHX_|gluEmwuY{cqtwP}S&itV-'
        ')+u|USby;ldraP3YF4;6~QdF%d){j@+s%gbK*~5S3>QFXyH%-%YG}^SyF3I!F@o;QKo+ssQ-'
        '?WFMsO#oXP`%MemF<edovgoVs!Av*#qCNr`hBtAm-Tj%d?$W5ih3nv?R9Y|R#nk;qSG}^k*sle#CH1Ouj@zCXMNo'
        '5ACsa>>b)-'
        '77xfwn;NO0&@y7?nZ6)$!y%z1qwmgV7zZPGtzT9lSxGmoOa@q>41HDYeJx~vj)7_0n3H*KiP^=EWYr5`h^>{+Xzc'
        '0%AYa+B)-'
        'mFDsi?V0nQP%t8p>whLvu*Y*Rs7?gs4P4EOHq|TIkA?{z99h5>wMSTi=C(sZuj}26nR%{ME+5f+dJqfzb$p|mUVL'
        '7I^P$MRa2}HhtX&)Hi>Px6Gc6~FRG*HW-xnGn6$Pn9w&*c!OODb>Z@b}fDSY2sTIJCwJaG!wc=j1#a1Y28bUXhpP'
        'A{qX<^*Z_3GH(3ppZ~)MHUO2v9kRLs%T*Cd*&QkD^<NdJXiOCAUpe!LSkY!*O4U1s|gQzLX;(%#t}iDB5iY6dw}?'
        'ljK8Lujgq;6PIRGx!fcme5^An<zVP@F`Hf8EG>8#IKhPH^tqr?w}KoW)R13dRV2lriu}T>+%`uXRta)ULuvEHpV}'
        'h~!s&l;Gg~IVn0tkYtAw&`o8w*rSRHrWaW}Sbfu6~Yt;I2h>cERDsCpRFL(2#5=rX6h8P3`5lNTN>B)|tV=IiP8g'
        'kkSunkBD1+^1M6lVd-CQmrgbE|RjMW&x+_`+0J0*+9w117Wc_R#je=AH-Pxu8Ug2cszx$8XX|a`&y3NE*`aXZOgj'
        'MJ2VPpU54e$DvR@kj0qBnee$>D4^0iM#eXSbLZo19p14a)Cah;Y!4oS=bL3Y?$^eP7+rZEcV*Hp*i>exD0i`7>_`'
        'f7h@e%r$>gi^B4LtiA{(ph64sEd)KQ`rh3~JyZlU?maixwmY#P!#K0qD;m<Q16HSeX87*BYz3X?I{yegv;zPGduo'
        'pp6HDtg5CHy743-1}bj5{LobM8*z2>HcLd+38KU+4Vg0zJeaT^G!F^1vN-_n@(#+!5mrdFeV&CjdC*W)q8@7*gpp'
        '`4Q|u_eExHo4);vku=3`D;AeBSlLTW6@P8?d`@toAM<aBASXMIMPS&4n~QM5COl`OHtMq{Ylq(ygVC*c^EvI(NOh'
        'A|XG38x9OE=q9r>*;U6qxx-I?8J=8B^hDlG}kK2p-'
        'eTSsh?bX0{u9IuekQ9QQ=rAlUfF~5Y2!CJDYGYnG3>>j>~w6t!YIb$`K?rKYSF>y)YpB5qT(1<dkF+2b42x`$%Gm'
        'tTBt@tE5FSAQ-nb%xMKmae>{*DFPRExrB-fsZG%luVHSuc7pyj3fw6NJ+$k%3bMQd@Hit)w*tH)fNJTAY;UUr!y}'
        '?IXVmgJ5;m`^ijPJAp)IM(yQW#^n_^d1k0&Y-'
        'ZBNu$mmMgHPO{5T#jZKFE{Vh0hz>*Q0H+Sk+@2)cQf0boYLM;QBas`8U!as+#$Xi99Prsms<B>W*(nmT2Aaj`(OG'
        '0=jcxf!I<r=?%(NilGN$*$k}IeMvf(nSNyrxi^UAFOxe^G`cPTtE<`UckT2)a<g;<^eLdozHR4mw8mxVqB43+M1<'
        '(JN+JVzdLszEj9cci|fS`aM%9jU+X#Btr^?Q5tTvOE3-'
        ';>EOstH_js0C(55`z{VK>mP+r=2UtjF7Lc@`wbdrk#Qnxzz~UbB2;sE3F+pRMA{g}U?vF~vR^}u`07_SbXhObwz='
        '&DICg8GTW%`5J)-k;3XH4jpuJlVX%Xn6bQbET;dZ2U+-'
        '6iX+{)@5x2Y{3ZZ9>E+g6sj?Vdbqt^7dl291?ihk=P7jzxVaE1^~}kr2gTC}7_<x5aH)m4_0W=}?zkwrGcp+yPnA'
        '8vxMJj7S7PEexQ(taRa0epjydO<5nDMYgv{1|hwkzGZ7&S*{$|t|apa01T{GUQM=IRpeiofDP0a?S5=Yh06~O)Px'
        'JNj2t6Y3w<JozDqrOO#FbEtO38&H?Jw6HG>uhHC5JW^V~PR#ORI{ut9G%pwXwNpX}wq(h$7=jwp3o)a#Gs`fvxn2'
        'ZbKXdy#{=?Hu#AEsk9W`ZWKr7Oo*+Ht!sVSCWM$xtrH4;O9Cyk`U6;<CvZH=>rJu!xRhzOwQQT=cyVQR8imhDw>f'
        ')RZ9i8j!P0$hfaZ4+X#Cqr!X{`KbHHr9UZ6p>zi}}Cimu=KHkcYck1I^8nIinM(I;EvA@2_I&<P2guzhXpt+|1-'
        'r|4n=)ZS8i1rktc&!c;Z3ruPKCrFu<ShS*SpwA?^6aJB*NCy?S1!myVOSMMQXfjR(=`27qFW^0u4z!<ZjW7Ai>|x'
        'UI4A$6a85pmwicCU;Y5JT3SN_#jtJPF?u2Do^sI`+fcUPg?gh9fK$l}B66|7|9H2o5E=vV=q1gb@aa*HZ6EO0WNP'
        'R$I0t)fi9g=VU^V_6b6_uDK$=66XSp&Ml_zSo{&=YM06ojK-bc83{wp@c3ci)s4N&>ja_urFFc}UPYSH<I%B<c6x'
        'CxBG5lF(77Rba7%(zD&MC6^A>>js3l>85h*o3bvdgd$mpl5)p7==snjxM)v`RuofBcoq#chD@3dHy%TNrLP2eyB9'
        'BBgK09Brvs5|bzCXqP~z(YcS|8tJlX0sPp}1HyO1rFubV|SC8Q|HS<UT?&ZV#2{Qxe&u6P*h-pJ2Z&3<?d()+_N-'
        '#YkOW#S?|LBW4b;{MCG3V>vpoY)0`j1krqg2e^z&Gd^m@6;{`JV%Ny2qew6{03%g93nq)08^MvR{tuwURsFcHq>J'
        'YoocC$XoY}-'
        'hSkKF=mri54EyyYfpx`~5_c;_b5veXLjrw4Ej?|IF;4*UA{k!+5tR3&{cd2@t(`?lwJ8EY???XxM6<ACtYuVN#1w'
        'gbyrKsGjL}!6nP5arIXYvW;35e}4r6{N>ts@iR4NXD)oIn`Vos<6>R*uKX0VdjA7T00MhBZEFa0Ju$mcBksP~Bk#'
        '9WgADUzhC<PAleJuEmTRPUu<Z=^H{c!;1e$lXx<^5**8mlNvd?G13m8%9m73D#S^_f$c<eX(+}o_KIy!X!xHFFKf'
        '!TsFM}*Q43OBEbj}R-O~^K#omwqCnS8i|+8a7h@u`-'
        '8*64GXTpq8_CHa$cvjL5KVr)UMlraZg+(yfn~o}7KYkySeM66O#v8pB$hkSs|1U2GFPIk#&2l0E%Z#$ui0!map?3'
        'q1X*`{C81ArFE0_)8pk-7W2BbK_)$agut#ZoEB6|dI@F+FIo<NMujc9-'
        'TRCiGTtHe>xms!J`v%PASWcO20b^^{VxD4kwM3Ez8`Zd+8xCoqhBC8ba>ylB)k@Tdme@&-'
        'MNJcKR6+waXEQZZ|CIc@5c@>b&2f8|G{*yYWa#BI)zR2V?L|n)MRg^0!;cNvWN|O*<l~*F6|^GRh>x(62Ml(CXJx'
        '=Feh}mw;D{0lVs~8KCBP4&o$|fN9vMI`VQT35^&2%24x!Z=4Hh1X5EGB4j0-'
        '18B{qjSNq>usj$b8AwCdbY+N~$Ep3xglxT%1(o!tbD6L1GU^fn(23<=*V8(rd>1GCugiXAwEXJrChx>L!#&{ebBg'
        'Z1uUQA*nqD`3)yFAL&Y?vA^BC4faS!mPa3U_IKOVqn*tEV7_is73t&>YL4fzWCf&c+&V@*{5ps<$bYw)H*2FzbOd'
        '>3#}D&`mv_XUzJ3OVjs%^2kXp$M)ROVTgsE!0ennxeLk2RFw`8>1kVYOk+`2VGeCBUGHhqY$pTO~xw!y+IR(>eXO'
        'HFi`2tx~FA<;{g60|IfdRx(_xI`*9n_9}Fbb>P3_Wy<Q4lx$<cBYk6oVBuO!1`k3h5J__4JcsPeY2q6L}0X^#!Bw'
        '8AfB|wgg5wK0W>PXw*M&!$yUXG``EefKmlYrv4Ge6Vv69;D|zDbV+>WL|i4R$>yrj2{m`IUUQ>yQ5~uO+=P(HXdt'
        'AMZVLeM|5O~L;%^I38Yjruw;OfIPSlf=3?yYNKSQccr)y}Tx)t^6ZdbG)QdgqRlcoV4IQ=L#{Xcc;FP`>+Den^+H'
        'q&Pb%l{D~c{1TpNwT@a$D<Pw;CR-~IexiVM;<u|R%9)06>TZ2f|dpA5>^PUkl{R)V+YG+13lwguzH!I@-'
        'gP<yUaY(rPjc^{ozsiE0L~Pegf@!-'
        '3yaXi>n{zb%7B);QA>7WTD$GedB2!Ktq}HXGXxD!HSmh0$<8bGPzu@n(fVgtV*ubBfo>c5B2bO7cWt9g1wFsOoE6'
        '}3Q#ae#R!?%K5#7WRZs8Tj>N;hsYR{3x=P%vnE@i(WlRYRcbwR^MNKTm>k<?4=4rVFg)UOmyZ7kgnUc)SNUD!J(H'
        '4iMH9?Zy&DbCo&>o4;o>HL=IJU*=gCJHjP+uh+n*Dx7(L|P8CknmMeB0@Xevh%nH;z9I&+ErA*7gR1v432GP}2og'
        'SUS%Ya`K7e#_K;nHbfA^oROE#C}bcPThZjnMw8?V6woi3#0<9PMPI}LzCnPm-'
        '*^zSKBhIzjQ~u{ydii+jY!g9Ta>UC`3r^^zi!*69jB6acet5zE8rh0#5%d5O`g}Ovm}9Tcf|v$aoT<8NVSb6Zf<x'
        '^?i&PKZLkItd9iH;9n^TXsy!!HyKh&m13?jMy9M<-'
        'SbeOT8q+dpdj*GG9=e1bSGn30D~wf8jA5$xi4?nH@3{b$s{CYcP~$<)_KjM5Ub55VX3g?i$*;8jb|b#oD4K=lH8s'
        'zptyQmDOBox*u<?4)RV~~r4+jo7*v~R}SrO$pWGBXW4m=OnILKAg56Z!a+n*tTYf(4g{U|N$5C3Is3@=SjYFoplB'
        'ke7{j&7H*&Z0ST0Y_3DZTyvRu*m7ED)(clbQob?B~CwAnyoWOT}WsX511~!wr!M}0N1ZZ{}v1yC@@^tjdj*J&uMb'
        'f&MDi)324w7KF0+-'
        'Zv>T9wFWm$D;+3uGU6jHTr9)JIsKs&3`M0`+)pdV1t7mr345^q!T1N1V8{bUwTx_PAS50FbRo$n=Rq3IiKo!?#3K'
        'i5*q>xOI+6EoM{q{cyCvMjiGlSeIJx8xGo6qmoC!u@ydXwd7JD)QpfiYkMpE)QX9YOTPMs0(N#?o=QoeF#(=a~I?'
        'XH7i%p~)UVhhK<z{@aV!?{`)q$sEBTq^W+G~GCwYV7ODXJivUE0frd*@UwLV~9+d7k6|fiBeH{!CCoEJ)0<(<~p6'
        'Zz4WZ;vcF!oUYpK6MJKmAwt_at<?=}FeqsV<S+5QZLCWyyjKii}SF^b<x2>UfG)+(yEX6oFx{OY1fpLEoqVFdIvC'
        'IJ#%W(QNdyak!Sk(un8PNJsv`t6qTFz6ZH4va}%mwX{#ScjbSve}s;&v|~eY`6xkzgQ-rCAiW!1hvIDiYZSa=#h~'
        'L3DO?s>8pF69isp8c=sjNpF?q1qG;nB_hk1zQc4iW!qpST{krnZOjmR-'
        '#2Y+7Y9j9ki2!LnhHeFHi4x9ZYm+`P#cpvp#Z81&hc1s_%Ubgkn8q0Y=elmLR{o{>E!Vs4EcHG!19kJ;Wl}Enc)('
        '?TNr4|C0~IUVqlv~AieB^)He#G9!K~6-'
        '0hTfuz}5;h%Sl&`3I_i_h}g^pJ)+sS$v|V9_oXK)CqOYH8?UVx*RM~F8SIX%)~)N&Wh?2#3Mt_p-'
        'Q9_al_p?SZZYpJCS*f2iNLRf+i8H?<qFrfn0U|U6DI@61H^@u*z1pEK(mA&$*Om+rSp;j5A5!b#uf!BS0(;pKW9F'
        'XFUNcZzgCC9j2b-'
        't=L!P3ee^F*vFl~D95Ecus`)=0C~qK9=MwvZop>!F$!nnz)xr8j<EIdu(KJ<h=n!|6j)y>3m08OyL-nf%T;>ira!'
        '%7%)<VJkDO(BAaf9*&vYI$hA}??Te}BlL#*8;*>g@xTh_9?YWaXMs^tdT#L(+x8&K9!9=A!C(!?KW%@N-'
        '{>fFlF+?m*})ft;mI!k6?p9@3{tnK!2H@B$9)-IZi`RyZh7pz|-'
        'JM|)c8REUj8!3tIMh}c6JS1_EG`YvyB!m3yl;{)B&q<3j<upbQY5aa}qQuYeKu2KkJAU_pQV%^53~#B-'
        '&tLalRMCIh*6Hz_bG1M7e1+N(=gUkH?V^rjip?dS6L2D98tWo%eH@;6R)>77kuh#X%{Ts9@WYzj6nv`!+=INWw`1'
        '4+aE+G1fV2W-'
        'WXI6+)=DZt0TTsv@09Yk1^;<`Jz>^hl2A^7Ey%p=11Rb|BcPy9qTG_j5b@m>1@>3m(!?3d%;+rO)sT5)L~CKlvh2'
        'V3fer3gflX17u~#1YCl0%Dlw&qLXs)4KtrZd|)Myg9Y=9i5%jeR=F)INvEJ_iAsC|}AvM)+J3`~iZVAohOr{1#8r'
        'P!fU!_&R>W=8Dsi;1i1brLl7eZdt`11?h}SP;ME$y^ghhchBtMr&`WibHO-'
        'E3@@|Q6CC<c140*_=Ld2A?lG!z@>W-'
        'XJU@mfW+z}VPo3^od&y>$HCs2^I+j+Nix{2e#s+0BOBXyFo=jKunrqQEFtyD(Q^K1d!(LjsBpTT&qJ1pq!<Df>Z9'
        'n*#|W2Py+jVT5hIO*$@3B@wmEI8sch(GJLYK|ta0YY^iSpB2VGp8j(M5yb0UZG;@q<=K1EWfqW2p))0Fj1Q$GNIs'
        '<Oy6La54+@I#>{57$Z9dknJ6N#Q)6TI+hfW}{vYlE#1`AfKqQu$1FN22b2xin^#C$tQL1*9d@pirSnMI0sMjNBM_'
        'cv69ZtIp(f5Wpgt~zZopsPNXucd{`wvgOCQKOx<gs+zO+9`@uyaU``yrMk!_#+<TT>t<`gY|HX?>y_W=R*zRloi6'
        'XR5k)eCXgrbmur>VVv!ayi2MI_WUl}lhhNNv38z5(@LpwK^5c6&~ZF`noojR%`Y)r`9)#tcSR<lN_j@Uz~hPyM$+'
        'aFOq=b*U=g?Lx(RPD@fIpPtUWY2s-'
        '>=cp4$n8TyA&y<R8AIGFmU{TYw>V^t)6kGi)I=Sy4Q<yV$bjmnFl;kpeW1qW3!@XkUY=zhK(ByQPNUAOw@^e9hG!'
        '^M)$=WtYC7gXkEqW2zX>M1F7I(^YKUlKN=tOUSGj)p!wj1kxoe+q=N?`zyA8k}X2l?M_1P%Emi+;S+4rXsBLkJtg'
        '6HBJ(shxLs;21b<yeRqr2$fMZ^VlJ<Y0FF>zC8s|pUITAY%3ahajCwdjPfw>xc1;AxY)!@qleJ5sBNyO=XW_#M<='
        'zggP?1`Xb~|bf%kpIr<j28zgOo14t&T#&_hIscnsWF7}glXThG*>`>`BdZgb9NWS+n^J7IzO?oX7`$_F`@$2`}=1'
        'nCBxjsYv%Kgc1U<Fwz=>w8>2-'
        'Tt%>do;_Fu(Fdiv|t2lnBk^RgHO+MTTVF=0|NGRB7A44rLHC!cDvmgXGRNnl>0;%k;NiMFk}gLgS8)L791Qv`t*#'
        'Pvo^Fn?Avlzw2$Tzf|K}r$axD{c~Q{WQ_vq5xEQaHt`W>)Q$B!@6V`GudOz<+cNPizd=#yGm{Z;@KOscu22JijnF'
        'ekAK@N4~bm8DP*jF+zu#wMa=Z*9v*3q$^ppQG!^H7eA^&AqJ<7W~<uun&wB7J^pt<$f(!Xdc7m)E%<;nryf>V%O7'
        'Z8Lv5#O!KAAXnjP^IONQdp8c^8wjDY_xT{KLGn7cQac$IP8Vf<EwYDv^hR}w(yCO~aHrp>Hkc=ip~H3R@q5@Koe3'
        'R;x=BB|WO+(9#eH*Zhrvs<-=72Cr)qx(-AMvqdUbW|fY;r&?zTZh*Un=%Zr{pN+2QS;-m<gT6-'
        '^zPglg7@N@MEXc-Coe_|Vf%m?!R+^|TF@6f_PCds_GD5TsAfqaH~9DS&=|*5A+@w9EYtb-'
        '48xGozDB;)0PS5Z<q?zn`L^X<hF2t$L-^;9_(z{xxtu>=~D-8?9`;!dIvLjuS3&>N-'
        '1vV?D8|i}6IScQ+ZG8(@t>3-'
        'rX~9~L%^d%dT~8d;K=d)iNNqiYIe(2N_<6Rk+Y^H%Z_xIS@_TAFTRmS1~n#&*urS#(3a2SPL)7)?u@^llt^XB6>j'
        'j=qzN(G_#lVi?EY9$cGyv7<@AlLJ8=H-~iY{_Jl?Inwie{~X6+=6%=T>jPijqH6A0-'
        '2Nj=Dv&*<Tj*!bPM^Kdz9$V@UjCl{6(<z;tW}sN^MdCDIubfJcf4Bwv`I9>UZ`{UoaroBVA>ilrd_F86P+0zp11u'
        '3sE$8~$85%7W3rk=4IY7e3O^A$0;V(Bp89)3LL`5ac_?9*i)cqqAIpB&?2U*4WS=_bZnA6;9;Jtst25vsl7rA>W?'
        'TSB-'
        '4|?(pSquoiZf52M&aVi1^$L<K=40i`(%l|h1mDEd7tL8mNoQR7plkTyW5<j(!dn5s^&ZS3QTeYoC6T{MP$z51LxJ'
        'B%iyd47oFad0!}5HF0*Q?<BpO*7U@P5_)1p1YkpU3fu_eb{g4|F6Mhl?dPB9u;jURz75N$s`|c^L>L%*DeF<u9-'
        ';@^I1BbKfRG(T}#TP?CDh^3KhQs>cOr>5}HTy?!nZ%yG<xZjCj+8bcwL0++Y(de&t-'
        'kc%C8boQB?;D$I8@DQF`MXFSWa=1F;^Sb?kPKWO7v7M`)*TO$m^8o#GhBmdHaWVX%yWvqjodBTdVpt`K~CzcOnwx'
        'oxqoBj@6k=Q$Fi`t?i3vUQ8(A(os*-'
        '%T#^DX4V{blyw#<6{JgjyE1^!jD{l~kQInsWnZpl>A>v)I&^r<THH(6*X9Y%qe`rHl#xP%?QUC!QtiAksS9a2d+L'
        'f&c?d6oL7!>cfKDzdf~>~V!8HDGEL%Yqa|e!+SZmNJJAw%c8<Pm-gGK0NEkWgv!$X*8cj;ZqY%e@UGuj6JJNA<Kh'
        'Y8IbD^j4eV8!JWfaueH<8|BkB5WzCzMbFnB0jM%Q_)AQWIi>f=F9e3mIW6N&#m*L(968LZ8^R5sc4IWG>ah;=KM6'
        '?&WTcvafjQY?NDRLabeVezNiaFWp__L;SB3~=lE5gAi~v0vh#o+{I{oQ{GpM|_s#Xj_Hmc`r`su*6k-'
        '36*B{s%Jpge6a#(UZ+E|}`x7Ql$L|!)+gHhA8cOy|3U|=RZGPKC#M`|t1J8drF19vVoQ)p0=@Rd5zuKDP^HkOP0s'
        'no)*UqNBvvM0`^xFZLX2X+IX&%Gl*v?5>jqi2IGXcXskRhnh5k#PFG^t3+}#<af+Os|GDF!|d9CJRphGsz)7Ik^b'
        'wuk2~?t|RtLO}ImRvBMPZ6~3Ci!Yh;09Q8xO-'
        'z}8tN<D2^O`J$kAIxf*I|KX~=X~Ci<2ubE)?7Z~xan86Ihc9xY)b=EgI96*WnO)w`BYu=I|5e@*LBi@D2}q#S_+g'
        '78--iXVUQWG1Uz!20l-'
        'uiMncl9C}cRA*OrB`H#)j=#@p~my>GzNmv2V=zrHDtIe@*so$_uyt)WWo%~&B{(kZrDhFZ}s(Vcl|xJ-'
        '9d*r7aB$WN*RPr(%rWhYOuqvmAl#;ex~b-|<b-=Q*IoE7R{3+oSrXtF5}=y_Ruy+#Diw)(BC-'
        'j4`4mLeKwO~2J`z(vP*A0)MdfpQD~#TpP`*tO_ZZMmm<xYQC4ha@~6m|_y=u>-'
        'L99*LHY?W@y0v>a4DG`D}n9;WH=E4_wh7krIFNw>6N%A%m1gmdRN{iLS&Df#dJN))7oK^mO;Z$$?a)bV#`oaO;n$'
        '48jpKTcxd&Hou_^m9Pin|yJY+`4W<&=Xpx6nX;FQQzJMFycwZ`6=^WtX9X}u`1|VE4)`z)q3viGkEI$Q3Y?12fmK'
        'h38($~gy{eJ%-+4Zk9Xfc-F@BQ{NOuS=-MSPOn9k|yd1Op-'
        '!k9kb#J*z<9zN^i`~AIt6u{&u|S9C+ced(@fk$^>r3$QIl#2-'
        'ZPCvTf4VCv^ib5pG?6d$3pBaZ1u^BX*+r@mIh{Y5JHk~#-'
        '~9SgaY|@U39LI`=Q+<)Le5!goDyC=Q*vI^^_*5f4U+UiLln_7NIK-'
        '2U3k^bnZfAGgLu(Ro!iG;&FR^1zI|?tnH&=3>+#vOcT1YK>}lksB`)5;90zp<e{8^iddj@OZ*REN*(tPjKHC{cXV'
        '`$Y6jnT0Zif&IQ8PRRgCw>KyE>GYXv$&*iJ+P@S5G`_N!PGxcv<q5fBRVwxg3Q@$&fHtYP$3?K`Vn_v`@)hfrwB{'
        '>QLf7fE_@wYVj%w`5Ks6M322pP?o2EZSYN!APi#7(9I$g)f&n$uBGHceJ(lK*~@TLNr!Y{Pb~l=!nDm^$jo)kmqw'
        'P^L%Vqye~*u^Opzb;F1~~?byM5W)dnAdqAv0lDO*!L>IoU}nz4{U)f{panQ(yW^4MbEf$1;ywJT`jY`l6Hbih~B='
        'EZ{u&l2EX9a@iU#xFcnw^!Mq4!wL2s__eUc$cPw@TQVz<R*%@jt`oILARW5B18j9I+ou9UdNt&@N9Qs5WK!`#DrG'
        '@E^%w{380dET^8HAp*PS34oei}pjkYzvafdUp~5f+ha<ZIc!=QQQ>u+Q7ES5LMA>;=NI#yW)ECmGaGVI%l1KfDwg'
        '%f8rJsK02VA&H(3;>ZYu&3Jv{F37@*eBrz9=i1wc#ac;6>aljQ*K7g6*iiOB^Kjo}CS2YBJO7Y=s(T$=R!kSha}P'
        'z%dOJfE!C=)SQ9?7o5UWuUSJklo8U#`w+Sc^gRW~NOcy7haT%Q5FZ4$D)z-'
        '~S<%kLTqS;~(WLSHVD>UN`2|p9y+AShg>3vQ@HvZBRdn4L)*3&GTJ6G7QSuujvfl|l-'
        ')Wlu0mhGS71v9ZtER3V!N{vunSvkO9r3l~w~u=5(qf>a1%aTug4NA|cx172la8cYY?1^#Idak``1^h+nC4YRiLvh'
        '-)-2mo2RG8p(e1uUJC!Ti_nclE)!&7^a5Gj#Y86-ut|(N%HReBJvC!<*Q2%V-'
        '!XW|vaj))tBRw_11^=pX#kbtHk8I_t7p$@cT_W8a853Zp&o{6BXzq>X7jQUA!;0I?mmk~4SyEi4=>`-'
        'XzxT{DSWm${rIC9thu(c<&rI}QS<!a^yqdQuy@MEEM6P@AG74i?WS;v%NauP_5>i?*$*=jrUcqa}Fd4b|jpw4tXM'
        'WCq*eaaPbN++B&4A@6&7+xJdS0_YZTPD}XN4Xcp>R@X;%h-Y{=v7|D!m<w*qFWdfQUX<pSDXo#JT;-'
        'h{gsu=RX((rWWUe-VAfY96dSbN4lLSF*c9BjZV{vxAra_V!dkxJZJstvT)v*gfS*R`vraH-'
        '<af$#b6X(eseLScm$9ZW*&PV?FGb^tv^3@%)-t4@0Y%WD;SIr-'
        'ODu1ncC(IjbnmNk)(J_W6L(Dljq%wB8OpMjn6l2m<*fen758^Bwa|;9x5ai(M+T62|Qem{s$zfgzx'
    ),
    '_portable_underwriter_0e3c6ff3ba97.reporting._core': (
        'c-p;K+iu)85PjdTAoL^^YoS1ZUJR%}<GMhBItiSleFzMKD^Y7U6seNb+D_ts@9-'
        'jtx;aK38U)@I=ge?sG;=uIBuTDhMfsVaol%4%smfcb;j3X%pjs+Kjz>k0#89MYE0xixR<c35l!{iUg+HvcV4WvPv'
        'fDW!#&u^pMKMOKu}X*tA&oPt1E!Rm)1XNXWe>a}ZOg=QkKWRMJ1R=*(G@sgSVMc*`*#=nVbMccVs1G*^oTd`xZ8z'
        '?mWYaI1pnKr_t6T-'
        'fm7UximE%s3|07h`l9@yu3sF;&p+lqVDKiNU~Wyr`&|^Zf`#}Swx}363aJe%b#EO1qou%_)O3%qqLA@Q?@>v3*>M'
        'ORM=Ia2Aw99mCb-`%-'
        '68mQ8CI`t`nB1+MOP!e#4lYtI~P(IdLK~XjpD|lF&*I9H#o;c+ZjD|?LzXd5wF!>goA7Qu-'
        '3FhG04+<!Ga&}NAupxOQodRkiBkQ32sQQsqT0%E2L@&XP+qcZes7Fjc<qFT)%$#=j9cCdwKQit9O4~yglzL`2%#*'
        'e)<4^Zf;P4K0CWft$e9JB<EqtEi0;9@QlK0a={5}&<Na*u(1Oz@Qr_h&Mdc8PBxLw?&W<eH8g50Ejx9h_}*>XHMY'
        '{&i6R=1NZ*n*{KE|Iwm&OnC(K0U(SIbGo+u>xt1%C_XNSC|F-'
        'GjII={Xi^i~khh+D6Redv_HR=OScOMoB;c}B>GHSquWewT4R?smJ1*5DfB753*u-'
        '~`_|zME@B8hQ?Voc~4)`Q1Kw6W{p{QkstN^VP18PMukwP0=?Vu1V7Z?c7mzyfy0<Yf9{a1?Kv5$Jz_}vNO=>*d8$'
        'Fwt3MPce;3C&vWyJk16v8G+s$Tq37+#R1qsrwej9F7Pe%OX2F@d)^riY+6Lvojlj6fsl;TtrXt&r)GeNzD`n{Hmo'
        '3^n_a&bse_IhE(3!l3k`ab50ku1yEGC16E0~aZKU!F0@P;HmK|KXW!H@nMj4E4Br<qd@XG*cf<mpiJ^;nH#DHi@?'
        'T#l-+h`x`2N!=BbrxDawUeSLUMgCP6{$pI8z1L#)9O?V;i+R>OA`3<0PH@P|<V2t4qVO5Y*Ao+jPvs{-'
        'R?`&n6Cj)U>0MZ)X%;`wYc;}Gg`2utYLQ061Z%nmmy~m?p@<gg%@>e3ClV&02AhX=MKP9+Iu$Slu|(0zJF1pi!-'
        'Bb^kluh>lu?K*uBL3-'
        'RKrAAY|L_Ll(%T`i`mTf;pfNY`oMDW&N^HG?1pPoZ5l?brHlIo6=V@rgFQ>oX++#v4ksMk0y<4qn)NyBnV}Afx$f'
        '$k-'
        'RIn9FwKA|4A2JpoaA<@Pxi=tNgmIK_!ME9B1gh*%uJJLQ`B^DKEf5j8gV9UdYlOu8eKh*2QEo941<m_8)^vLZOCL'
        'sa1z4|w+H*82Ap6&1;^F2rW4EU=*<bd;RM?#QIdI+{i!p05ZBn6)vr~fpLgV)#_%dCu)wKEV|tnI_=zeRSQ9%v2I'
        'ZlgYEauk%w2~YC=WPLt|9Rzov;qP{wB@l4jieVa3O|}I#YsTf9=eLyi4ICn&rR~wLMczYS(p3%K`>m=#fe%iv-FR'
        'e_VZqRxkrEm}E`y3AzcRc0+`1C+j<~Z@Rp#e0Z`rZlV~X)=nHbSgV}rA(IisXZuM_EAK*olTG{X&x0(6`-'
        '`7ty+spvN)m2*9BjFZWqwOZm98f?%O*zbFB_wwJ#zZCO9!V$4{{hNntq6w=Ri?65HrK53vRfwkKx6TNsK_Dig?h5'
        'Y7B{0D@eFvhpyKh6efbnt2)t!3KL`dwfU?+G3Zy~tz~EL@SN2XW6^TB2}FFH!&wR&<;};6snkE{;+^Us^Yk8E#`2'
        '?kj7dCqlN@%_$i~ksX_T|Tq|m)UxNyqDBwi$)sn32&`eV-'
        '6%hJZMIv#Bie;59Hbol#9E#{>=BF3^QR!V8a4GdU3!GBxCRy>RN;E35_On?+HoG%~zG`{}hNVvTvTNCuA+$S#?Zn'
        'qm(J^<Y8{sT)vxxo'
    ),
}
# fmt: on


def _new_package(name: str) -> None:
    if name in _sys.modules:
        return
    package = _types.ModuleType(name)
    package.__file__ = f"<embedded-package:{name}>"
    package.__package__ = name
    package.__path__ = []
    _sys.modules[name] = package


def _load_embedded_runtime() -> None:
    _new_package(_RUNTIME_PREFIX)
    _new_package(f"{_RUNTIME_PREFIX}.reporting")
    for name, payload in _EMBEDDED_SOURCES.items():
        if name in _sys.modules:
            continue
        module = _types.ModuleType(name)
        module.__file__ = f"<embedded:{name}>"
        module.__package__ = name.rpartition(".")[0]
        _sys.modules[name] = module
        try:
            source = _zlib.decompress(_base64.b85decode(payload)).decode("utf-8")
            exec(compile(source, module.__file__, "exec"), module.__dict__)  # noqa: S102
        except Exception:
            _sys.modules.pop(name, None)
            raise


_load_embedded_runtime()
_core = _sys.modules[f"{_RUNTIME_PREFIX}.reporting._core"]
_evidence = _sys.modules[f"{_RUNTIME_PREFIX}.reporting.evidence"]

UnderwriterReportError = _core.UnderwriterReportError
UnderwriterReportOptions = _core.UnderwriterReportOptions
UnderwriterReportResult = _core.UnderwriterReportResult
build_scored_model_report = _core.build_scored_model_report

CapabilityUnavailable = _evidence.CapabilityUnavailable
EvidenceFact = _evidence.EvidenceFact
EvidenceRequest = _evidence.EvidenceRequest
ExactLossEvidence = _evidence.ExactLossEvidence
FeatureImportanceEvidence = _evidence.FeatureImportanceEvidence
InteractionEvidence = _evidence.InteractionEvidence
MainEffectEvidence = _evidence.MainEffectEvidence
ModelEvidence = _evidence.ModelEvidence
SuppressionMetadata = _evidence.SuppressionMetadata

ProblemType = Literal["frequency", "severity", "burn_cost"]
ColumnOrValues = str | Sequence[float] | np.ndarray | pd.Series
ComparisonUnit = str | Sequence[Any] | np.ndarray | pd.Series
_ALLOWED_SECTIONS = {"report", "data", "columns", "predictions"}
_ALLOWED_KEYS = {
    "report": {
        "output_path",
        "title",
        "model_type",
        "tweedie_power",
        "top_k",
        "double_lift_bins",
        "curve_bins",
        "distribution_bins",
        "movement_bins",
        "comparison_bootstrap_replicates",
        "comparison_bootstrap_seed",
        "minimum_cell_size",
    },
    "data": {"path"},
    "columns": {"actual", "sample_weight", "features", "comparison_unit", "offset"},
}


def build_report(
    frame: pd.DataFrame,
    *,
    actual: ColumnOrValues,
    predictions: Mapping[str, ColumnOrValues],
    sample_weight: ColumnOrValues,
    features: Sequence[str],
    model_type: ProblemType,
    output_path: str | Path,
    offset: ColumnOrValues | None = None,
    comparison_unit: ComparisonUnit | None = None,
    evidence: Mapping[str, ModelEvidence] | None = None,
    title: str = "Pricing model review",
    tweedie_power: float | None = None,
    minimum_cell_size: int = 20,
) -> UnderwriterReportResult:
    """Build a self-contained aggregate report from already-scored predictions."""
    options = UnderwriterReportOptions(
        title=title,
        problem_type=model_type,
        tweedie_power=tweedie_power,
        minimum_cell_size=minimum_cell_size,
    )
    return build_scored_model_report(
        frame,
        actual=actual,
        predictions=predictions,
        sample_weight=sample_weight,
        features=features,
        output_path=output_path,
        evidence=evidence,
        offset=offset,
        comparison_unit=comparison_unit,
        options=options,
    )


@dataclass(frozen=True)
class PortableReportConfig:
    data_path: Path
    output_path: Path
    actual: str
    sample_weight: str
    features: tuple[str, ...]
    predictions: dict[str, str]
    options: UnderwriterReportOptions
    comparison_unit: str | None = None
    offset: str | None = None


def _required_string(table: Mapping[str, Any], key: str, label: str) -> str:
    value = table.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _config_path(
    raw_value: Any,
    *,
    label: str,
    relative_to: Path,
    suffixes: tuple[str, ...],
    suffix_message: str,
) -> Path:
    if not isinstance(raw_value, str) or not raw_value.strip():
        raise ValueError(f"{label} must be a non-empty path")
    path = Path(raw_value.strip()).expanduser()
    if not path.is_absolute():
        path = relative_to / path
    resolved = path.resolve()
    if resolved.suffix.lower() not in suffixes:
        raise ValueError(f"{label} {suffix_message}")
    return resolved


def _features(raw_value: Any) -> tuple[str, ...]:
    if (
        not isinstance(raw_value, list)
        or not raw_value
        or not all(isinstance(value, str) and value.strip() for value in raw_value)
    ):
        raise ValueError("[columns].features must be a non-empty string array")
    resolved = tuple(value.strip() for value in raw_value)
    if len(set(resolved)) != len(resolved):
        raise ValueError("[columns].features must not contain duplicates")
    return resolved


def _predictions(raw_value: Any) -> dict[str, str]:
    if not isinstance(raw_value, dict) or not raw_value:
        raise ValueError("[predictions] must be a non-empty table")
    resolved: dict[str, str] = {}
    for raw_name, raw_column in raw_value.items():
        name = str(raw_name).strip()
        if not name or not isinstance(raw_column, str) or not raw_column.strip():
            raise ValueError("[predictions] must map non-empty names to non-empty column names")
        if name in resolved:
            raise ValueError(f"[predictions] contains duplicate normalized model name: {name!r}")
        resolved[name] = raw_column.strip()
    return resolved


def _optional_number(raw_value: Any, label: str) -> float | None:
    if raw_value is None:
        return None
    if isinstance(raw_value, bool):
        raise TypeError(f"{label} must be numeric, not boolean")
    if not isinstance(raw_value, int | float):
        raise TypeError(f"{label} must be numeric")
    return float(raw_value)


def load_config(path: str | Path) -> PortableReportConfig:
    """Load a prediction-only portable report TOML file."""
    config_path = Path(path).expanduser().resolve()
    with config_path.open("rb") as handle:
        payload = tomllib.load(handle)
    unknown_sections = set(payload) - _ALLOWED_SECTIONS
    if unknown_sections:
        raise ValueError("unknown TOML sections: " + ", ".join(sorted(unknown_sections)))
    for section, allowed_keys in _ALLOWED_KEYS.items():
        section_payload = payload.get(section)
        if not isinstance(section_payload, dict):
            raise TypeError(f"TOML section [{section}] must be a table")
        unknown_keys = set(section_payload) - allowed_keys
        if unknown_keys:
            raise ValueError(f"unknown [{section}] keys: " + ", ".join(sorted(unknown_keys)))
    report = payload["report"]
    data = payload["data"]
    columns = payload["columns"]
    title = report.get("title", "Pricing model review")
    if not isinstance(title, str):
        raise TypeError("[report].title must be a string")
    title = title.strip()
    if not title:
        raise ValueError("[report].title must be non-empty")
    model_type = report.get("model_type")
    if model_type not in {"frequency", "severity", "burn_cost"}:
        raise ValueError("[report].model_type must be frequency, severity, or burn_cost")
    features = _features(columns.get("features"))
    predictions = _predictions(payload.get("predictions"))
    comparison_unit = columns.get("comparison_unit")
    if comparison_unit is not None:
        if not isinstance(comparison_unit, str) or not comparison_unit.strip():
            raise ValueError("[columns].comparison_unit must be a non-empty string")
        comparison_unit = comparison_unit.strip()
        if comparison_unit in features:
            raise ValueError("comparison_unit must not also appear in features")
    offset = columns.get("offset")
    if offset is not None:
        if not isinstance(offset, str) or not offset.strip():
            raise ValueError("[columns].offset must be a non-empty string")
        offset = offset.strip()
    options = UnderwriterReportOptions(
        title=title,
        problem_type=model_type,
        tweedie_power=_optional_number(report.get("tweedie_power"), "[report].tweedie_power"),
        top_k=report.get("top_k", 12),
        double_lift_bins=report.get("double_lift_bins", 10),
        curve_bins=report.get("curve_bins", 100),
        distribution_bins=report.get("distribution_bins", 200),
        movement_bins=report.get("movement_bins", 10),
        comparison_bootstrap_replicates=report.get(
            "comparison_bootstrap_replicates",
            200,
        ),
        comparison_bootstrap_seed=report.get("comparison_bootstrap_seed", 1729),
        minimum_cell_size=report.get("minimum_cell_size", 20),
    )
    return PortableReportConfig(
        data_path=_config_path(
            data.get("path"),
            label="[data].path",
            relative_to=config_path.parent,
            suffixes=(".csv", ".feather", ".parquet"),
            suffix_message="must end in .csv, .feather, or .parquet",
        ),
        output_path=_config_path(
            report.get("output_path"),
            label="[report].output_path",
            relative_to=config_path.parent,
            suffixes=(".html", ".htm"),
            suffix_message="must end in .html or .htm",
        ),
        actual=_required_string(columns, "actual", "[columns].actual"),
        sample_weight=_required_string(
            columns,
            "sample_weight",
            "[columns].sample_weight",
        ),
        features=features,
        predictions=predictions,
        options=options,
        comparison_unit=comparison_unit,
        offset=offset,
    )


def _read_configured_frame(config: PortableReportConfig) -> pd.DataFrame:
    required_columns = list(
        dict.fromkeys(
            [
                config.actual,
                config.sample_weight,
                *([config.comparison_unit] if config.comparison_unit else []),
                *([config.offset] if config.offset else []),
                *config.features,
                *config.predictions.values(),
            ]
        )
    )
    if not config.data_path.is_file():
        raise FileNotFoundError(f"configured input file does not exist: {config.data_path}")
    suffix = config.data_path.suffix.lower()
    if suffix == ".parquet":
        return pd.read_parquet(config.data_path, columns=required_columns)
    if suffix == ".feather":
        return pd.read_feather(config.data_path, columns=required_columns)
    return pd.read_csv(config.data_path, usecols=required_columns).loc[:, required_columns]


def build_report_from_config(config: PortableReportConfig) -> UnderwriterReportResult:
    """Read configured scored columns and build the portable report."""
    return build_scored_model_report(
        _read_configured_frame(config),
        actual=config.actual,
        predictions=config.predictions,
        sample_weight=config.sample_weight,
        features=config.features,
        output_path=config.output_path,
        offset=config.offset,
        comparison_unit=config.comparison_unit,
        options=config.options,
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a self-contained model review from scored predictions."
    )
    parser.add_argument("--config", type=Path, required=True, help="Path to report TOML")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    result = build_report_from_config(load_config(args.config))
    print(f"Report: {result.output_path}")
    print(result.metrics.to_string(index=False))


__all__ = [
    "SOURCE_SHA256",
    "CapabilityUnavailable",
    "EvidenceFact",
    "EvidenceRequest",
    "ExactLossEvidence",
    "FeatureImportanceEvidence",
    "InteractionEvidence",
    "MainEffectEvidence",
    "ModelEvidence",
    "PortableReportConfig",
    "SuppressionMetadata",
    "UnderwriterReportError",
    "UnderwriterReportOptions",
    "UnderwriterReportResult",
    "build_report",
    "build_report_from_config",
    "build_scored_model_report",
    "load_config",
]


if __name__ == "__main__":
    main()
