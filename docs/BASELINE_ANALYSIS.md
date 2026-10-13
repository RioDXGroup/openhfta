# Baseline numérico

Executado em 2026-07-19 no checkout atual:

```text
make -B
python3 -m unittest test_hfta -v
./hfta.py --profile test/pro/PR1T-torre1-332.00.PRO --freq 20m
```

O build forçado do núcleo Fortran terminou sem erro. Antes da refatoração, os
27 testes existentes passaram. Após a refatoração, os mesmos 27 continuam
passando.

## Caso de referência

Entrada: `test/pro/PR1T-torre1-332.00.PRO`  
Comando: `./hfta.py --profile test/pro/PR1T-torre1-332.00.PRO --freq 20m`  
Frequência efetiva: `14.2 MHz` (`20m`)  
Antena: Dipole, uma altura de `10 m`, convertida para `32.8084 ft` antes da
chamada interna  
Solo: epsilon relativo `13.0`, condutividade `0.005 S/m`  
Difração: habilitada

Saída textual observada:

```text
Profile 1 (PR1T-torre1-332.00.PRO):
  Maximum gain: 10.0 dB at 27.25°
```

Vetor produzido:

- 140 amostras, de `0.25°` a `35.00°`, passo `0.25°`;
- primeiros valores: `[-30.0, -30.0, -2.5660925, -0.9492406, 0.4702614, 1.4525527, 1.5036731, 1.5677500, 1.9059062, 2.1825819]`;
- mínimo: `-30.0 dB`;
- máximo: `9.999393463134766 dB` em `27.25°`;
- SHA-256 de `pattern_db.tobytes()` (`float32`): `4657d80a8d6a8997631f479f6ca7b7c52592cc368b6f8066adf407e9510f9819`.

Não havia arquivo AoA no caso de referência, portanto não há FOM a registrar.

## Tolerâncias de regressão

Comparações de padrão usam `float32` com tolerância absoluta `1e-5` dB e
relativa `1e-5`; ângulos devem ser idênticos; pico usa tolerância de `1e-5` dB
e `0.25°`. O hash é apenas diagnóstico: diferenças de compilador não devem
ser aceitas ou rejeitadas somente por ele. Os DLLs legados necessários para
comparação diferencial não estão disponíveis neste ambiente.
