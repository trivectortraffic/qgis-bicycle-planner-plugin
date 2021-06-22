## Regional cykelmodell 2.0

Utifrån utfallet av Kågesson-modellen 1.0 och de antaganden som skärskådades redovisas här en ansats till en regional cykelmodell 2.0. Den nya modellen beaktar exempelvis både cykel och elcykel för olika typer av ärenden, alltså inte bara pendling. Den nya modellen beaktar också olika grupper av människor utifrån exempelvis etnicitet, socioekonomi och ohälsa. Det är inte möjligt med tillgängliga data att beakta olika gruppers faktiska resmönster, däremot är det möjligt att beakta olika grupper när det gäller prioritering av infrastruktur. Såsom påpekats påverkas generellt socioekonomiskt svaga grupper mer av dålig infrastruktur. Från ett jämlikhetsperspektiv kan det då vara motiverat att satsa extra på svagare områden.

En utmaning är att göra välavvägda antaganden om hur länge och hur långt människor är villiga att cykla i relation till olika ärenden. Den här typen av information går inte att hämta från den svenska resvaneundersökningen. Istället har den nederländska resvaneundersökningen använts, se Figur   4 -23 och Figur   4 -24. Fördelen är dels att den nederländska resvaneundersökningen redovisar resmönster med både cykel och elcykel för olika typer av ärenden, dels att den nederländska cykelinfrastrukturen kan ses som en målbild.

.
.
.

### Modellen

Modellen är resultatet av ett examensarbete utfört av Laurent Cazor vid KTH. Huvudmålet för modellen är att rangordna nödvändiga förbättringar på basen av det relativa behovet för varje länk i vägnätet....


### Upskatta potentiellt behov av cykelvägar

Modellen är består av ett antal undermodeller för att beräkna behovet. Uppdelningen är både baserad på typen av ärende (pendlign till arbete, skolresor, turism, inköp och rekreation) och typ av cykel (vanlig cykel och elcykel). Orsaken till uppdelning baserat på cykeltyp beror på skillnaden i distans en person på vardera cykeltyp normalt färdas. De olika ärendena är baserade på den nationella resvaneundersökningen.

[fig]

Den modell som används för att uppskatta det potentiella behovet kallas fyrstegsmodellen. Denna modell är vedertagen i transportplaneringssammanhang och består av 4 nedan beskrivna steg där indata i det första steget är demografiska värden samt start- och målpositioner. Varje steg i modellen använder sig av resultetat från det föregående.

1. Resegenerering: Detta steg identifierar start- och målpositioner. Startpositioner är personers hem medan mål kan vara arbetsplatser, skolor, butiker, fritidsområden etc. Syftet med resegenerering är också att uppskatta antalet resor som varje ärende kan ge upphov till. Vikten av varje startposition är proportionerlig mot befolkningen och varje mål har samma vikt normaliserat till 1. Detta steg tillåter användandet av socioekonomiska variabler för att påverka vikten av startpositionen.

2. Resedistribution: I detta steg ämnar beräkna relationerna mellan start- och målpunkter samt sannolikheten att denna resa tas som en funktion av avståndet mellan en start- och målpunkt i relation till avstånden av övriga relationer i samma grupp. Modellen som används är en s.k. gravitationmodell. Utöver resultatet från föregående steg kräver även detta steg ett vägnätverk för att beräkna avståndet mellan start- och mål par.

3. Färdmedelsuppdelning: När start- och målrelationerna är kända (OD-par) kan sannolikheten för att en resa mellan ett par ska tas med cykel och elcykel beräknas. Detta modelleras på basen av faktiska resmönster sm en funktion av avståndet. Metoden som användas kallas "Binary logit model".

4. Summering: Antalet resor kan kan i det här steget beräknas genom att summera sannolikheten för varje OD-par per nätverkssegment. Summan representera det uppskattade dagliga flödet för varje del av vägnätverket.

Figure 2 visar ett flödesschema över varje steg beskrivet ovan.


[fig]


### Steg 1: Resegenerering

Målet med första steget är att identifiera resor och deras frekvens. Modellen har delats upp i flera undermodeller baserat på ärende:

- Arbetspendling
- Skolresor
- Inköp
- Övriga serviceärenden
- Rekreation
- Turism

Antalet resor per dag per person är baserat på den nationella resvaneundersökningen utförd 2019. Detta försäkrar att den beräknade mängden cykling överensstämmer med det potentiella dagliga flödet. För varje ärende _p_ definerar vi _T_p_ som antalet resor per individ per dag eller den s.k. resegenereringsfaktorn. Modellen gör antagandet att varje resa generera två enhetr _flöde_ (då varje mål kräver en tur- och en returresa). Undantaget är turismresor då de är mindre sannolika att generera returresor.

Den nationella RVUn skiljer inte på inköp och övriga ärenden samt rekreation och turism. Vi antar därför att fördelningen är 50/50 för inköp/övrigt och 75/25 för rekreation/turism. Tabellen nedan anger värdet för parametern _T_p_ för varje typ.

[table]

Det andra syftet med detta steg är att skapa start- och målpunkter.Vi definerar resegeneratorer och attraktorer för varje ärendetyp med antagandet att varje tur- returresa startar och återgår till en individs hem. Information om var individer bor aggregeras bl.a. på DeSO nivå. Sverige delas in i 5984 demografiska statistikområden vilka representerar mellan 700 och 2700 individer. Indelningen tar hänsyn till geografiska företeelser och begränsas i möjligaste mån av t.ex. vägar, vattendrag, järnväg etc. De är utformade att vara stabila över längre tidsrymder.

Målpunkter för arbetsplatser och skolor kan hämtas från SCB och då på nivån ruta. En ruta är ett område på 1000 m x 1000 m utanför tätort och 250 m x 250 m i tätort. Arbetsplatsmålpunkter kan delas in i 15 olika kategorier för att göra modellen mer detaljerad.

Övriga målpunkter kan hämtas från t.ex. OpenStreetMap, som är ett öppet fritt tillgängligt dataset, som innehåller en mängd klassade intressepunkter. Dessa OSM klasser kan kategoriseras för använding som målpunkter i modellen.


### Steg 2: Resedistribution

När de potentiella start- och målpumkterna är identifierad är nästa steg att modellera relationerna mellan dem i form av antalet resor mellan varje start- och målpunkt även kallat OD-par. Vi använder oss av en gravitationsmodell som säger att antalet resor mellan ett OD-par är proportionellt mot storleken på startpunkten, målpunkten och en generaliserad kostnadsfunktion mellan dem (vi använder oss av avståndet men även andra parametrar som höjdskilnad, säkerhet etc kan användas).

Matematiskt kan modellen beskrivas som följande: om _i_ är en startpunkt med storleken _O_i_ och _j_ är en målpunkt med storleken _D_j_ där avståndet  är _d_ij_ så är antalet resor mellan _i_ och _j_

$$
T_{ij} = A_i O_i D_j f(d_{ij})
$$

Där $A_i$ är en utjämningsfaktor som säkerstället att antalet resor som lämnar $i$ är lika med $O_i$. Vi får därmed

$$
A_i = \frac{
    1
}{
    \sum_j{D_jf(d_{ij})}
}
$$

Funktionen _f_ kallas avståndsavtagande vilken är en funktion vars värde avtar med avståndet. Vi väljer en exponentiellt avtagande funktion vars parameter är medelvärdet av den angivna reselängden för varje ärendetyp i den nationella RVUn.

$$
f: x \rightarrow e^{-\beta x}
$$

Värdet för $\beta$ anges i tabell 2

[tabell]


### Steg 3: Färdmedelsuppdelning

En färdmedelsvalsmodell, eller mer generellt en diskret valmodell, beräknar sannolikheten för att ett visst färdmedel ska användas som en funktion av olika parametrar. I det här fallet reslängd. Den aktuella modellen


