FFmpeg Embed Kit (Windows)

O que é
-------
Este kit baixa um build oficial do FFmpeg (BtbN/FFmpeg-Builds) e copia os executáveis
necessários para execução portátil do seu app:
  - ffmpeg.exe
  - ffprobe.exe
  - ffplay.exe

Como usar
---------
1) Coloque este kit na RAIZ do seu projeto (onde existe a pasta 'app').
2) Abra o PowerShell nessa pasta e execute:
   powershell -ExecutionPolicy Bypass -File .\embed_ffmpeg.ps1
3) Após finalizar, verifique:
   .\app\bin\ffmpeg.exe -version

Observações
-----------
- Por padrão baixa: latest/ffmpeg-master-latest-win64-gpl.zip (BtbN).
- Você pode trocar a fonte usando o parâmetro -SourceUrl:
    powershell -ExecutionPolicy Bypass -File .\embed_ffmpeg.ps1 -SourceUrl "https://www.gyan.dev/ffmpeg/builds/packages/ffmpeg-release-essentials.zip"
- Os arquivos de licença serão copiados para: app\licenses\ffmpeg

Licenças
--------
O FFmpeg é licenciado sob GPL/LGPL (dependendo do build). 
Ao redistribuir o seu app com FFmpeg embutido, inclua os arquivos de licença copiados para app\licenses\ffmpeg.
